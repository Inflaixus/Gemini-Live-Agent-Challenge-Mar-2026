/**
 * ADIOU – browser client
 *
 * Handles WebSocket connection, microphone capture (16 kHz mono PCM),
 * playback of model audio (24 kHz mono PCM), text chat, and
 * optional diarization rendering.
 */

// ---------------------------------------------------------------------------
// DOM refs
// ---------------------------------------------------------------------------
const chat       = document.getElementById("chat");
const status     = document.getElementById("status");
const statusText = document.getElementById("statusText");
const btnConnect = document.getElementById("btnConnect");
const btnMic     = document.getElementById("btnMic");
const btnVideo   = document.getElementById("btnVideo");
const btnImage   = document.getElementById("btnImage");
const btnPdf     = document.getElementById("btnPdf");
const btnSend    = document.getElementById("btnSend");
const responseMode = document.getElementById("responseMode");
const textInput  = document.getElementById("textInput");
const fileImage  = document.getElementById("fileImage");
const filePdf    = document.getElementById("filePdf");
const videoPreviewWrap = document.getElementById("videoPreviewWrap");
const videoPreview = document.getElementById("videoPreview");

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let ws = null;
let captureCtx = null;
let playbackCtx = null;
let mediaStream = null;
let workletNode = null;
let isRecording = false;
let nextPlayTime = 0;
let videoStream = null;
let videoTimer = null;
let videoCanvas = null;
let isVideoOn = false;
function getOrCreateStableId(key) {
  const existing = localStorage.getItem(key);
  if (existing && typeof existing === "string" && existing.trim()) {
    return existing;
  }
  const created = crypto.randomUUID();
  localStorage.setItem(key, created);
  return created;
}

let userId = getOrCreateStableId("adiou.userId");
let sessionId = getOrCreateStableId("adiou.sessionId");
const VALID_OUTPUT_MODES = new Set(["both", "text", "audio"]);
let outputMode = localStorage.getItem("adiou.outputMode") || "both";
if (!VALID_OUTPUT_MODES.has(outputMode)) {
  outputMode = "both";
}
const VIDEO_MAX_DIM = 768;
const VIDEO_JPEG_QUALITY = 0.85;
const VIDEO_FRAME_INTERVAL_MS = 1000;

// ---------------------------------------------------------------------------
// UI helpers
// ---------------------------------------------------------------------------
function setStatus(text, cls) {
  statusText.textContent = text;
  status.className = cls || "";
}

function addMessage(text, role = "system", speakerLabel = "") {
  const div = document.createElement("div");
  div.classList.add("msg", role);
  if (speakerLabel) {
    const lbl = document.createElement("div");
    lbl.className = "speaker-label";
    lbl.textContent = speakerLabel;
    div.appendChild(lbl);
  }
  const span = document.createElement("span");
  span.textContent = text;
  div.appendChild(span);
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return div;
}

/** Update or create a message bubble for partial transcripts. */
const partialBubbles = { user: null, model: null };
function upsertTranscript(role, text, partial) {
  if (partial) {
    if (!partialBubbles[role]) {
      partialBubbles[role] = addMessage(text, role);
    } else {
      partialBubbles[role].querySelector("span").textContent = text;
      chat.scrollTop = chat.scrollHeight;
    }
  } else {
    if (partialBubbles[role]) {
      partialBubbles[role].querySelector("span").textContent = text;
      partialBubbles[role] = null;
    } else {
      addMessage(text, role);
    }
  }
}

function setConnectedUI(connected) {
  btnConnect.textContent = connected ? "Disconnect" : "Connect";
  btnConnect.classList.toggle("active", connected);
  btnMic.disabled = !connected;
  btnVideo.disabled = !connected;
  btnImage.disabled = !connected;
  btnPdf.disabled = !connected;
  btnSend.disabled = !connected;
  textInput.disabled = !connected;
}

function applyOutputMode(mode, announce = false) {
  outputMode = VALID_OUTPUT_MODES.has(mode) ? mode : "both";
  localStorage.setItem("adiou.outputMode", outputMode);
  responseMode.value = outputMode;
  if (outputMode === "text") {
    resetPlayback();
  }
  if (announce) {
    const label = outputMode === "both"
      ? "🔊 + 📝 Both"
      : outputMode === "text"
        ? "📝 Text only"
        : "🔊 Audio only";
    addMessage(`Output mode: ${label}`, "system");
  }
}

// ---------------------------------------------------------------------------
// WebSocket
// ---------------------------------------------------------------------------
function connect() {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  ws = new WebSocket(`${proto}//${location.host}/ws/${userId}/${sessionId}`);
  ws.binaryType = "arraybuffer";

  ws.addEventListener("open", () => {
    setStatus("Connected", "connected");
    setConnectedUI(true);
    addMessage("Connected to agent.", "system");
  });

  ws.addEventListener("message", (event) => {
    if (event.data instanceof ArrayBuffer) {
      if (outputMode !== "text") {
        playAudio(event.data);
      }
    } else {
      handleJson(JSON.parse(event.data));
    }
  });

  ws.addEventListener("close", () => {
    setStatus("Disconnected");
    setConnectedUI(false);
    stopRecording();
    stopVideo();
    addMessage("Disconnected.", "system");
    ws = null;
  });

  ws.addEventListener("error", () => {
    setStatus("Error");
    addMessage("WebSocket error.", "system");
  });
}

function disconnect() {
  stopRecording();
  stopVideo();
  if (ws) {
    ws.close();
    ws = null;
  }
  setStatus("Disconnected");
  setConnectedUI(false);
}

// ---------------------------------------------------------------------------
// JSON message handler
// ---------------------------------------------------------------------------
function handleJson(data) {
  switch (data.type) {
    case "transcript":
      {
        if (outputMode === "audio") break;
        const label = data.role === "user" ? "🦷 Dentist" : "👩 Chloe";
        upsertTranscript(data.role, `${label}: ${data.text}`, data.partial);
      }
      break;
    case "interrupted":
      resetPlayback();
      break;
    case "diarization":
      addMessage(data.text, "model", data.speaker);
      break;
    case "error":
      addMessage(`Error: ${data.message}`, "system");
      break;
    case "go_away":
      if (typeof data.timeLeftSeconds === "number") {
        addMessage(
          `Live session will refresh soon (about ${Math.max(0, Math.round(data.timeLeftSeconds))}s left).`,
          "system"
        );
      }
      break;
  }
}

// ---------------------------------------------------------------------------
// Mic capture  (16 kHz mono PCM via AudioWorklet)
// ---------------------------------------------------------------------------
async function startRecording() {
  if (isRecording) return;
  try {
    captureCtx = new AudioContext({ sampleRate: 16000 });
    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
    });

    const source = captureCtx.createMediaStreamSource(mediaStream);

    await captureCtx.audioWorklet.addModule("/static/pcm-processor.js");
    workletNode = new AudioWorkletNode(captureCtx, "pcm-capture");
    workletNode.port.onmessage = (e) => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(e.data);
      }
    };

    // Keep audio graph alive without playing mic back to speakers
    const silentGain = captureCtx.createGain();
    silentGain.gain.value = 0;
    source.connect(workletNode);
    workletNode.connect(silentGain);
    silentGain.connect(captureCtx.destination);

    isRecording = true;
    btnMic.classList.add("recording");
    btnMic.textContent = "🔴 Stop";
    setStatus("Recording", "recording");
  } catch (err) {
    addMessage(`Mic error: ${err.message}`, "system");
  }
}

function stopRecording() {
  if (!isRecording) return;
  isRecording = false;
  if (workletNode) { workletNode.disconnect(); workletNode = null; }
  if (mediaStream) { mediaStream.getTracks().forEach((t) => t.stop()); mediaStream = null; }
  if (captureCtx) { captureCtx.close(); captureCtx = null; }
  btnMic.classList.remove("recording");
  btnMic.textContent = "🎤 Mic";
  if (ws && ws.readyState === WebSocket.OPEN) {
    setStatus("Connected", "connected");
  }
}

// ---------------------------------------------------------------------------
// Image / PDF helpers
// ---------------------------------------------------------------------------
function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const result = reader.result || "";
      const base64 = String(result).split(",")[1] || "";
      resolve(base64);
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });
}

async function handleImageFile(file) {
  if (!file || !ws || ws.readyState !== WebSocket.OPEN) return;
  try {
    const base64 = await blobToBase64(file);
    ws.send(JSON.stringify({
      type: "image",
      data: base64,
      mimeType: file.type || "image/jpeg",
    }));
    addMessage("🖼 Image sent.", "user");
  } catch (err) {
    addMessage(`Image error: ${err.message}`, "system");
  }
}

async function handlePdfFile(file) {
  if (!file || !ws || ws.readyState !== WebSocket.OPEN) return;
  if (file.size > 50 * 1024 * 1024) {
    addMessage("PDF too large. Max 50MB for inline upload.", "system");
    return;
  }
  try {
    const prompt = (window.prompt(
      "Ask a question about this PDF (optional)",
      "Summarize this document."
    ) || "").trim() || "Summarize this document.";

    const base64 = await blobToBase64(file);
    ws.send(JSON.stringify({
      type: "pdf",
      data: base64,
      prompt,
    }));
    addMessage("📄 PDF uploaded.", "user");
  } catch (err) {
    addMessage(`PDF error: ${err.message}`, "system");
  }
}

// ---------------------------------------------------------------------------
// Live video (webcam → JPEG frames @ 1 FPS)
// ---------------------------------------------------------------------------
async function startVideo() {
  if (isVideoOn) return;
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    addMessage("Connect first to start live video.", "system");
    return;
  }
  try {
    videoStream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 768 },
        height: { ideal: 768 },
        facingMode: "user",
      }
    });
    videoStream.getTracks().forEach((track) => {
      track.addEventListener("ended", () => {
        if (isVideoOn) {
          stopVideo();
        }
      });
    });
    videoPreview.srcObject = videoStream;
    videoCanvas = document.createElement("canvas");
    videoPreviewWrap.classList.add("active");
    await videoPreview.play();
    isVideoOn = true;
    btnVideo.classList.add("active");
    btnVideo.textContent = "⏹ Stop Video";
    addMessage("📹 Live video started.", "system");

    videoTimer = setInterval(captureVideoFrame, VIDEO_FRAME_INTERVAL_MS);
    captureVideoFrame();
  } catch (err) {
    addMessage(`Video error: ${err.message}`, "system");
  }
}

function stopVideo() {
  if (!isVideoOn) return;
  isVideoOn = false;
  if (videoTimer) { clearInterval(videoTimer); videoTimer = null; }
  if (videoStream) { videoStream.getTracks().forEach((t) => t.stop()); videoStream = null; }
  if (videoPreview) { videoPreview.srcObject = null; }
  videoPreviewWrap.classList.remove("active");
  videoCanvas = null;
  btnVideo.classList.remove("active");
  btnVideo.textContent = "📹 Live Video";
  addMessage("📹 Live video stopped.", "system");
}

async function captureVideoFrame() {
  if (!videoPreview || !videoCanvas || !ws || ws.readyState !== WebSocket.OPEN) return;
  const vw = videoPreview.videoWidth;
  const vh = videoPreview.videoHeight;
  if (!vw || !vh) return;

  // Cap to VIDEO_MAX_DIM while preserving aspect ratio
  const scale = Math.min(1, VIDEO_MAX_DIM / Math.max(vw, vh));
  const w = Math.round(vw * scale);
  const h = Math.round(vh * scale);

  videoCanvas.width = w;
  videoCanvas.height = h;
  const ctx = videoCanvas.getContext("2d");
  ctx.drawImage(videoPreview, 0, 0, w, h);

  const frameDataUrl = videoCanvas.toDataURL("image/jpeg", VIDEO_JPEG_QUALITY);
  const base64Data = frameDataUrl.split(",")[1];
  if (!base64Data || base64Data.length < 100 || !ws || ws.readyState !== WebSocket.OPEN) return;
  ws.send(JSON.stringify({
    type: "video_frame",
    data: base64Data,
    mimeType: "image/jpeg",
  }));
}

// ---------------------------------------------------------------------------
// Playback  (24 kHz mono PCM)
// ---------------------------------------------------------------------------
function ensurePlaybackCtx() {
  if (!playbackCtx || playbackCtx.state === "closed") {
    playbackCtx = new AudioContext({ sampleRate: 24000 });
    nextPlayTime = 0;
  }
}

function resetPlayback() {
  if (playbackCtx && playbackCtx.state !== "closed") {
    playbackCtx.close().catch(() => {});
  }
  playbackCtx = null;
  nextPlayTime = 0;
}

function playAudio(arrayBuffer) {
  ensurePlaybackCtx();
  const int16 = new Int16Array(arrayBuffer);
  const float32 = new Float32Array(int16.length);
  for (let i = 0; i < int16.length; i++) {
    float32[i] = int16[i] / 32768;
  }

  const buffer = playbackCtx.createBuffer(1, float32.length, 24000);
  buffer.getChannelData(0).set(float32);

  const src = playbackCtx.createBufferSource();
  src.buffer = buffer;
  src.connect(playbackCtx.destination);

  const now = playbackCtx.currentTime;
  const start = Math.max(now + 0.01, nextPlayTime);
  src.start(start);
  nextPlayTime = start + buffer.duration;
}

// ---------------------------------------------------------------------------
// Text input
// ---------------------------------------------------------------------------
function sendText() {
  const text = textInput.value.trim();
  if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
  ws.send(JSON.stringify({ type: "text", content: text }));
  addMessage(text, "user");
  textInput.value = "";
}

// ---------------------------------------------------------------------------
// Event listeners
// ---------------------------------------------------------------------------
btnConnect.addEventListener("click", () => {
  if (ws) { disconnect(); } else { connect(); }
});

btnMic.addEventListener("click", () => {
  if (isRecording) { stopRecording(); } else { startRecording(); }
});

btnVideo.addEventListener("click", () => {
  if (isVideoOn) { stopVideo(); } else { startVideo(); }
});

btnImage.addEventListener("click", () => fileImage.click());
fileImage.addEventListener("change", (e) => {
  const file = e.target.files && e.target.files[0];
  if (file) handleImageFile(file);
  fileImage.value = "";
});

btnPdf.addEventListener("click", () => filePdf.click());
filePdf.addEventListener("change", (e) => {
  const file = e.target.files && e.target.files[0];
  if (file) handlePdfFile(file);
  filePdf.value = "";
});

btnSend.addEventListener("click", sendText);
textInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendText();
});

responseMode.addEventListener("change", () => {
  applyOutputMode(responseMode.value, true);
});

applyOutputMode(outputMode);
