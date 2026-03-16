# ADIOU – مساعد ثنائي اللغة · Bilingual Live Audio Agent

Real-time voice assistant with seamless Arabic ↔ English code-switching, powered by **Google ADK** and the **Gemini Live API** (native audio model).

## Features

- **Bilingual voice conversations** – speak in Arabic, English, or mix both naturally.
- **Native audio model** – uses `gemini-2.5-flash-native-audio-latest` for low-latency audio I/O.
- **Live transcription** – both input and output audio are transcribed in real time.
- **Output mode switch** – choose `🔊 + 📝 Both`, `📝 Text only`, or `🔊 Audio only` from the UI.
- **Text chat** – type messages alongside voice for a multimodal experience.
- **Images** – upload JPEG/PNG images for visual understanding.
- **Live video** – stream webcam frames (JPEG @ 1 FPS) for visual context.
- **Long sessions** – context window compression + session resumption.
- **PDFs** – upload PDFs (inline ≤ 50 MB) with a question prompt.
- **Speaker diarization** *(optional)* – identify different speakers via Cloud Speech-to-Text v2.
- **Multi-scenario support** – extensible knowledge base per OSCE scenario.

---

## Quick Start

### Prerequisites

| Requirement | Details |
|---|---|
| **Python** | ≥ 3.10 |
| **Google Cloud project** | With billing enabled |
| **API key** | AI Studio key (billed to GCP) |

### Step 1 — Configure environment

```bash
cp .env.example .env
# Edit .env with your GOOGLE_API_KEY and GOOGLE_CLOUD_PROJECT
```

### Step 2 — Install dependencies

```bash
pip install -e .
```

### Step 3 — Run the server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### Step 4 — Use the app

Open **http://localhost:8080** in your browser.

---

## Project Structure

```
project_root/
├── app/
│   ├── main.py                         # FastAPI entrypoint
│   ├── lifecycle.py                    # Startup initialisation
│   ├── api/
│   │   ├── websocket_gateway.py        # WebSocket endpoint + session handler
│   │   ├── health.py                   # Health check endpoint
│   │   └── protocol.py                 # Typed message schemas
│   ├── services/
│   │   ├── agent_service.py            # ADK Runner + run_config builder
│   │   ├── session_service.py          # Session management + resumption cache
│   │   └── diarization_service.py      # Optional speaker diarization
│   ├── agents/
│   │   ├── patient_agent.py            # Agent definition + prompt loading
│   │   └── agent_tools.py             # Custom tools (language, identity, scope)
│   ├── rag/
│   │   ├── retriever.py                # Keyword-based RAG retriever
│   │   └── knowledge_loader.py         # Lazy YAML loader
│   ├── core/
│   │   ├── config.py                   # Centralised settings (env + YAML)
│   │   ├── constants.py                # Application constants
│   │   └── logging.py                  # Logging setup
│   ├── models/
│   │   └── model_manager.py            # Modality resolution
│   ├── configs/
│   │   ├── runtime_config.yaml         # Audio, video, queue settings
│   │   ├── rag_config.yaml             # RAG scoring parameters
│   │   └── model_config.yaml           # Model + diarization settings
│   └── prompts/
│       └── system/
│           └── patient_system_prompt.txt
├── knowledge_base/
│   ├── general/                        # Global policies
│   └── scenarios/
│       └── scenario_1/                 # OSCE scenario YAML files
├── static/                             # Test UI (temporary)
├── docs/
│   └── websocket_protocol.md           # WebSocket API documentation
├── scripts/
│   ├── run_local.sh
│   └── setup_env.sh
├── tests/
├── terraform/
├── Dockerfile
├── pyproject.toml
└── .env.example
```

## Architecture

```
Browser (16 kHz PCM) ──WebSocket──▶ FastAPI ──LiveRequestQueue──▶ ADK Runner
                                        │                              │
                                        │◀─── audio + transcripts ◀────┘
                                        │
                                   (optional)
                                        │
                               Speech-to-Text v2
                              speaker diarization
```

## Configuration

All settings are loaded from environment variables (`.env`) with fallbacks
to YAML config files in `app/configs/`. See `.env.example` for all options.

## WebSocket Protocol

See [docs/websocket_protocol.md](docs/websocket_protocol.md) for the full
client ↔ server message specification.

## Adding a New Scenario

1. Create `knowledge_base/scenarios/scenario_2/` with YAML files.
2. Optionally create `app/prompts/system/scenario_2_prompt.txt`.
3. Set `SCENARIO=scenario_2` in `.env`.

## License

Private – internal use only.
