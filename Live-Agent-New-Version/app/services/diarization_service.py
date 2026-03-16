"""Optional speaker diarization sidecar using Cloud Speech-to-Text v2.

Enable via ENABLE_DIARIZATION=true. Requires a GCP project with
the Speech-to-Text API enabled and ADC credentials.
"""

from __future__ import annotations

import asyncio
import os

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_diarizer_instance = None
_init_attempted = False


class SpeakerDiarizer:
    """Buffers raw PCM audio and streams it to Speech-to-Text v2 for
    recognition with speaker diarization.
    """

    def __init__(self) -> None:
        from google.cloud.speech_v2 import SpeechAsyncClient
        self._client = SpeechAsyncClient()
        self._audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        self._result_queue: asyncio.Queue[dict | None] = asyncio.Queue()
        self._task: asyncio.Task | None = None

    async def feed(self, pcm_chunk: bytes) -> None:
        await self._audio_queue.put(pcm_chunk)
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._stream_recognize())

    async def segments(self):
        while True:
            segment = await self._result_queue.get()
            if segment is None:
                break
            yield segment

    async def reset(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        while not self._audio_queue.empty():
            self._audio_queue.get_nowait()
        await self._result_queue.put(None)

    async def _request_generator(self):
        from google.cloud.speech_v2.types import cloud_speech

        project = os.getenv("GOOGLE_CLOUD_PROJECT", "")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        recognizer = f"projects/{project}/locations/{location}/recognizers/_"

        config = cloud_speech.RecognitionConfig(
            explicit_decoding_config=cloud_speech.ExplicitDecodingConfig(
                encoding=cloud_speech.ExplicitDecodingConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                audio_channel_count=1,
            ),
            language_codes=settings.diarization_languages,
            model=settings.diarization_model,
            features=cloud_speech.RecognitionFeatures(
                diarization_config=cloud_speech.SpeakerDiarizationConfig(
                    min_speaker_count=settings.diarization_min_speakers,
                    max_speaker_count=settings.diarization_max_speakers,
                ),
            ),
        )

        streaming_config = cloud_speech.StreamingRecognitionConfig(
            config=config,
            streaming_features=cloud_speech.StreamingRecognitionFeatures(
                interim_results=True,
            ),
        )

        yield cloud_speech.StreamingRecognizeRequest(
            recognizer=recognizer,
            streaming_config=streaming_config,
        )

        while True:
            chunk = await self._audio_queue.get()
            if chunk is None:
                break
            yield cloud_speech.StreamingRecognizeRequest(audio=chunk)

    async def _stream_recognize(self):
        import traceback
        try:
            responses = await self._client.streaming_recognize(
                requests=self._request_generator()
            )
            async for response in responses:
                for result in response.results:
                    if not result.alternatives:
                        continue
                    alt = result.alternatives[0]
                    for word in alt.words:
                        await self._result_queue.put({
                            "speaker": f"speaker_{word.speaker_label}",
                            "text": word.word,
                            "start": (
                                word.start_offset.total_seconds()
                                if word.start_offset else None
                            ),
                            "end": (
                                word.end_offset.total_seconds()
                                if word.end_offset else None
                            ),
                        })
        except asyncio.CancelledError:
            raise
        except Exception:
            traceback.print_exc()
        finally:
            await self._result_queue.put(None)


def get_diarizer() -> SpeakerDiarizer | None:
    """Return the singleton diarizer, or None if disabled / failed."""
    global _diarizer_instance, _init_attempted
    if _init_attempted:
        return _diarizer_instance
    _init_attempted = True
    if not settings.enable_diarization:
        return None
    try:
        _diarizer_instance = SpeakerDiarizer()
    except Exception:
        import traceback
        traceback.print_exc()
        logger.warning("Diarization disabled — could not initialise SpeakerDiarizer")
    return _diarizer_instance
