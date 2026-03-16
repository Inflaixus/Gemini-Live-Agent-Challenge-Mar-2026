# WebSocket Protocol

## Connection

```
ws[s]://<host>/ws/{user_id}/{session_id}
```

- `user_id`: Stable client identifier (UUID recommended).
- `session_id`: Conversation session identifier.

The server accepts the connection immediately. Audio streaming begins
when the client sends binary frames.

## Client → Server

### Binary frames: Audio input

Raw 16-bit signed PCM, 16 kHz, mono. Send continuously while the mic
is active. The server performs voice activity detection (VAD) and
forwards audio to the Gemini Live API.

### JSON messages

| type | Fields | Description |
|---|---|---|
| `text` | `content: string` | Text chat message |
| `image` | `data: base64, mimeType?: string` | Static image |
| `video_frame` | `data: base64, mimeType?: string` | Live video frame (JPEG) |
| `pdf` | `data: base64, prompt?: string` | PDF document with optional question |
| `close` | — | Graceful disconnect request |

#### Examples

```json
{"type": "text", "content": "Hello doctor"}
```

```json
{"type": "image", "data": "/9j/4AAQ...", "mimeType": "image/jpeg"}
```

```json
{"type": "pdf", "data": "JVBERi0...", "prompt": "Summarize this document."}
```

## Server → Client

### Binary frames: Audio output

Raw 16-bit signed PCM, 24 kHz, mono. Play back directly via
`AudioContext({ sampleRate: 24000 })`.

### JSON messages

| type | Fields | Description |
|---|---|---|
| `transcript` | `role: "user"\|"model"`, `text`, `partial: bool` | Speech transcript |
| `error` | `message: string` | Error notification |
| `interrupted` | — | Model output was interrupted by user speech |
| `go_away` | `timeLeftSeconds: number\|null` | Live session will refresh soon |
| `diarization` | `speaker`, `text`, `start?`, `end?` | Speaker diarization segment |

#### Examples

```json
{"type": "transcript", "role": "model", "text": "Nice to meet you.", "partial": false}
```

```json
{"type": "error", "message": "Live connection dropped. Please reconnect."}
```

```json
{"type": "go_away", "timeLeftSeconds": 30.5}
```

## Session Lifecycle

1. Client opens WebSocket to `/ws/{user_id}/{session_id}`.
2. Server creates or resumes an ADK session.
3. Client sends audio (binary) and/or JSON messages.
4. Server streams back audio (binary) and JSON transcripts.
5. If the upstream Gemini Live connection resets, the server
   automatically reconnects using a cached session resumption handle,
   preserving conversation context.
6. On `go_away`, the client should expect a brief reconnection pause.
7. Either side can close the WebSocket normally.

## Session Resumption

The server caches session resumption handles (TTL: 2 hours). When the
Gemini Live API resets the upstream connection (normal close 1000 or
deadline expired 1011), the server reconnects transparently. The client
does not need to take any action.
