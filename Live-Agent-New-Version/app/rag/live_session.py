"""
Gemini Live API session — real-time audio dental patient.

Architecture:
  - Doctor speaks into mic
  - Live API transcribes (input_audio_transcription)
  - We intercept the transcript, run it through our RAG pipeline
  - RAG context is injected into the Live API session as text turns
  - Live API generates patient response as natural audio
  - Audio plays through speaker

Your local code handles: embeddings, FAISS search, topic filtering,
repeat detection, nudges, phase control, context building.
Gemini handles: voice in/out, VAD, language detection, barge-in,
affective dialog, natural speech generation.
"""
import asyncio
import re
import traceback
import pyaudio
from google import genai
from google.genai import types

from .llm import DEFAULT_MODEL, client, llm_call_gemini
from .controller import SessionState, update_state_from_doctor, maybe_fire_nudge
from .engine import (
    EngineConfig, build_context, build_chat_history,
    patient_user_prompt, filter_repeated_topics,
    llm_smalltalk_prefix,
)
from .retriever import Retriever, chunk_text
from .scope import (
    detect_smalltalk_intents, is_out_of_scope,
    looks_like_dental_osce, OUT_OF_SCOPE_REPLY,
    looks_like_consultation_dialogue,
)

# Audio constants
INPUT_RATE = 16000
OUTPUT_RATE = 24000
CHANNELS = 1
FORMAT = pyaudio.paInt16
INPUT_CHUNK_SAMPLES = 1600  # 100ms at 16kHz


def _is_confirmation_question(text: str) -> bool:
    t = text.lower().strip()
    patterns = [
        "is that right", "is that correct", "right?", "correct?",
        "you'd like", "you would like", "i understand you want",
    ]
    return any(p in t for p in patterns)


class LivePatientSession:
    """
    Real-time voice patient: Gemini Live API + your RAG pipeline.
    """

    def __init__(
        self,
        state: SessionState,
        global_policy_text: str,
        opening_chunk: dict | None,
        emotional_chunk: dict | None,
        nudges: list[dict],
        case_retriever: Retriever,
        config: EngineConfig,
        topic_bank: dict[str, list[str]],
        global_dental_retriever: Retriever | None = None,
        voice: str = "Kore",
    ):
        self.state = state
        self.global_policy_text = global_policy_text
        self.opening_chunk = opening_chunk
        self.emotional_chunk = emotional_chunk
        self.nudges = nudges
        self.case_retriever = case_retriever
        self.config = config
        self.topic_bank = topic_bank
        self.global_dental_retriever = global_dental_retriever
        self.voice = voice
        self._audio = pyaudio.PyAudio()
        self._session = None
        self._playing = False

    def _rag_process(self, doctor_text: str) -> str:
        """
        Run the full RAG pipeline on the doctor's text.
        Returns the grounded patient reply as text.
        This is the same logic as patient_reply_rag but returns text
        that we then feed to the Live API for voice synthesis.
        """
        doctor_text = doctor_text.strip()
        if not doctor_text:
            return ""

        # 1) Smalltalk
        intents = detect_smalltalk_intents(doctor_text)
        prefix = ""
        if intents:
            prefix = llm_smalltalk_prefix(
                intents, doctor_text, self.global_policy_text, llm_call_gemini
            )

        # 2) Out-of-scope
        if is_out_of_scope(doctor_text):
            msg = OUT_OF_SCOPE_REPLY
            if prefix:
                msg = f"{prefix} {msg}".strip()
            return self._remember(doctor_text, msg)

        # 3) Smalltalk-only
        if intents and not looks_like_dental_osce(doctor_text) and not looks_like_consultation_dialogue(doctor_text):
            msg = prefix or "Hello."
            return self._remember(doctor_text, msg)

        # 4) First turn — opening statement
        if not self.state.opening_done:
            self.state.opening_done = True
            opening = chunk_text(self.opening_chunk).strip() if self.opening_chunk else ""
            if not opening:
                opening = "Hello, I'm here for my appointment."
            if _is_confirmation_question(doctor_text):
                msg = "Yes, that's right."
            else:
                msg = opening
            if prefix:
                msg = f"{prefix} {msg}".strip()
            return self._remember(doctor_text, msg)

        # 5) Controller state + nudge
        update_state_from_doctor(doctor_text, self.state)
        nudge = maybe_fire_nudge(self.nudges, self.state) or None

        # 6) Retrieval
        case_matches = self.case_retriever.search(doctor_text, top_k=self.config.top_k)
        case_matches = [(s, c) for s, c in case_matches if s >= self.config.sim_threshold]
        matches = case_matches

        if self.state.debug_mode if hasattr(self.state, "debug_mode") else False:
            print(f"[DEBUG] Case matches: {len(case_matches)}")
            for s, c in case_matches[:3]:
                print(f"  - {s:.3f}: {c.get('topic', 'unknown')}")

        # Fallback: global dental
        if not matches and self.global_dental_retriever:
            gd = self.global_dental_retriever.search(doctor_text, top_k=self.config.top_k)
            matches = [(s, c) for s, c in gd if s >= self.config.sim_threshold]

        # Filter repeated topics
        if hasattr(self.state, "debug_mode") and self.state.debug_mode:
            print(f"[DEBUG] mentioned_topics before filtering: {self.state.mentioned_topics}")
        matches = filter_repeated_topics(matches, self.state, doctor_text, self.topic_bank)
        if hasattr(self.state, "debug_mode") and self.state.debug_mode:
            print(f"[DEBUG] After filtering: {len(matches)} matches")

        # Track topics
        reply_topics = {c.get("topic") for _, c in matches if c.get("topic")}
        self.state.last_reply_topics = reply_topics
        self.state.mentioned_topics |= {t for t in reply_topics if t != "emotional_profile"}

        # 7) Build prompt — this is what Gemini sees
        system = self.global_policy_text.strip()
        context = build_context(self.emotional_chunk, matches)
        history_text = build_chat_history(self.state, max_turns=4)
        user = patient_user_prompt(doctor_text, history_text, context, nudge)

        # 8) LLM call (text, for grounding — Live API will voice it)
        reply = llm_call_gemini(system, user, self.config.temperature).strip()
        reply = re.sub(r"^\s*(DOCTOR|DENTIST|PATIENT)\s*:\s*", "", reply, flags=re.I).strip()

        if prefix:
            reply = f"{prefix} {reply}".strip()

        return self._remember(doctor_text, reply)

    def _remember(self, doctor_text: str, patient_text: str) -> str:
        self.state.conversation_history.append(("doctor", doctor_text))
        self.state.conversation_history.append(("patient", patient_text))
        return patient_text

    async def run(self):
        """
        Main loop: connect to Live API, stream mic audio, receive voice responses.
        """
        live_config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=self.voice,
                    )
                )
            ),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            system_instruction=types.Content(
                parts=[types.Part(text=self.global_policy_text)]
            ),
        )

        print(f"[LIVE] Connecting to {DEFAULT_MODEL}...")
        async with client.aio.live.connect(
            model=DEFAULT_MODEL, config=live_config
        ) as session:
            self._session = session
            print("[LIVE] Connected. Speak as the doctor. Ctrl+C to exit.\n")

            # Run mic input and audio output concurrently
            async with asyncio.TaskGroup() as tg:
                tg.create_task(self._send_audio(session))
                tg.create_task(self._receive_audio(session))

    async def _send_audio(self, session):
        """Capture mic audio and stream to Live API."""
        stream = self._audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=INPUT_RATE,
            input=True,
            frames_per_buffer=INPUT_CHUNK_SAMPLES,
        )
        print("[MIC] Listening...")
        try:
            while True:
                data = await asyncio.to_thread(
                    stream.read, INPUT_CHUNK_SAMPLES, exception_on_overflow=False
                )
                await session.send_realtime_input(
                    audio=types.Blob(data=data, mime_type="audio/pcm;rate=16000")
                )
        except asyncio.CancelledError:
            pass
        finally:
            stream.stop_stream()
            stream.close()

    async def _receive_audio(self, session):
        """
        Receive responses from Live API.
        When we get a transcript of what the doctor said, run RAG,
        then inject the grounded reply as a text turn so the model
        voices it naturally.
        """
        out_stream = self._audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=OUTPUT_RATE,
            output=True,
        )
        transcript_buffer = ""

        try:
            async for response in session.receive():
                server = response.server_content
                if server is None:
                    continue

                # Handle interruption
                if server.interrupted:
                    self._playing = False
                    transcript_buffer = ""
                    continue

                # Collect input transcription (what the doctor said)
                if server.input_transcription and server.input_transcription.text:
                    transcript_buffer += server.input_transcription.text
                    continue

                # When turn is complete and we have a transcript, run RAG
                if server.turn_complete and transcript_buffer.strip():
                    doctor_text = transcript_buffer.strip()
                    transcript_buffer = ""
                    print(f"\nDOCTOR: {doctor_text}")

                    # Run RAG pipeline
                    patient_reply = await asyncio.to_thread(
                        self._rag_process, doctor_text
                    )
                    print(f"PATIENT: {patient_reply}\n")

                    # Inject grounded reply into session so model voices it
                    await session.send_client_content(
                        turns=types.Content(
                            role="model",
                            parts=[types.Part(text=patient_reply)],
                        ),
                        turn_complete=True,
                    )
                    continue

                # Play audio output
                if server.model_turn and server.model_turn.parts:
                    for part in server.model_turn.parts:
                        if part.inline_data and part.inline_data.data:
                            self._playing = True
                            await asyncio.to_thread(
                                out_stream.write, part.inline_data.data
                            )

                # Output transcription (what the patient said)
                if server.output_transcription and server.output_transcription.text:
                    pass  # Already printed above from RAG

        except asyncio.CancelledError:
            pass
        finally:
            out_stream.stop_stream()
            out_stream.close()

    def cleanup(self):
        self._audio.terminate()
