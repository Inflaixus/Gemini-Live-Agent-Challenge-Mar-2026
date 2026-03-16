import { useState, useEffect, useCallback, useRef } from 'react';

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

export interface TranscriptMessage {
  role: 'user' | 'model';
  text: string;
  timestamp: number;
}

interface UseLiveAgentReturn {
  isConnected: boolean;
  isRecording: boolean;
  status: ConnectionStatus;
  connect: (voiceName?: string) => void;
  disconnect: () => void;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  startVideo: (existingStream?: MediaStream) => Promise<void>;
  stopVideo: () => void;
  isVideoOn: boolean;
  error: string | null;
  transcripts: TranscriptMessage[];
  clearTranscripts: () => void;
}

// Audio Worklet Processor code as a blob
const PCM_PROCESSOR_CODE = `
class PCMCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.buffer = [];
    this.bufferSize = 2048;
  }

  process(inputs) {
    const input = inputs[0];
    if (input && input[0]) {
      const samples = input[0];
      for (let i = 0; i < samples.length; i++) {
        this.buffer.push(samples[i]);
      }
      
      while (this.buffer.length >= this.bufferSize) {
        const chunk = this.buffer.splice(0, this.bufferSize);
        const int16 = new Int16Array(chunk.length);
        for (let i = 0; i < chunk.length; i++) {
          const s = Math.max(-1, Math.min(1, chunk[i]));
          int16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        this.port.postMessage(int16.buffer, [int16.buffer]);
      }
    }
    return true;
  }
}

registerProcessor('pcm-capture', PCMCaptureProcessor);
`;

function getOrCreateStableId(key: string): string {
  const existing = localStorage.getItem(key);
  if (existing && typeof existing === 'string' && existing.trim()) {
    return existing;
  }
  const created = crypto.randomUUID();
  localStorage.setItem(key, created);
  return created;
}

export const useLiveAgent = (): UseLiveAgentReturn => {
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [isRecording, setIsRecording] = useState(false);
  const [isVideoOn, setIsVideoOn] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [transcripts, setTranscripts] = useState<TranscriptMessage[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const captureCtxRef = useRef<AudioContext | null>(null);
  const playbackCtxRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  const videoStreamRef = useRef<MediaStream | null>(null);
  const videoTimerRef = useRef<number | null>(null);
  const videoCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const videoElementRef = useRef<HTMLVideoElement | null>(null);
  const nextPlayTimeRef = useRef(0);

  const userIdRef = useRef(getOrCreateStableId('liveagent.userId'));
  const sessionIdRef = useRef(getOrCreateStableId('liveagent.sessionId'));

  const VIDEO_MAX_DIM = 768;
  const VIDEO_JPEG_QUALITY = 0.85;
  const VIDEO_FRAME_INTERVAL_MS = 1000;

  // Playback functions
  const ensurePlaybackCtx = useCallback(() => {
    if (!playbackCtxRef.current || playbackCtxRef.current.state === 'closed') {
      playbackCtxRef.current = new AudioContext({ sampleRate: 24000 });
      nextPlayTimeRef.current = 0;
    }
  }, []);

  const resetPlayback = useCallback(() => {
    if (playbackCtxRef.current && playbackCtxRef.current.state !== 'closed') {
      playbackCtxRef.current.close().catch(() => {});
    }
    playbackCtxRef.current = null;
    nextPlayTimeRef.current = 0;
  }, []);

  const playAudio = useCallback((arrayBuffer: ArrayBuffer) => {
    ensurePlaybackCtx();
    if (!playbackCtxRef.current) return;

    const int16 = new Int16Array(arrayBuffer);
    const float32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) {
      float32[i] = int16[i] / 32768;
    }

    const buffer = playbackCtxRef.current.createBuffer(1, float32.length, 24000);
    buffer.getChannelData(0).set(float32);

    const src = playbackCtxRef.current.createBufferSource();
    src.buffer = buffer;
    src.connect(playbackCtxRef.current.destination);

    const now = playbackCtxRef.current.currentTime;
    const start = Math.max(now + 0.01, nextPlayTimeRef.current);
    src.start(start);
    nextPlayTimeRef.current = start + buffer.duration;
  }, [ensurePlaybackCtx]);

  // Handle incoming JSON messages
  const handleJsonMessage = useCallback((data: any) => {
    switch (data.type) {
      case 'interrupted':
        resetPlayback();
        break;
      case 'error':
        setError(data.message);
        break;
      case 'go_away':
        console.log('Session will refresh soon');
        break;
      case 'transcript':
        // Only add non-partial (complete) transcripts
        if (!data.partial && data.text && data.text.trim()) {
          setTranscripts(prev => [...prev, {
            role: data.role,
            text: data.text.trim(),
            timestamp: Date.now()
          }]);
        }
        break;
    }
  }, [resetPlayback]);

  // Clear transcripts
  const clearTranscripts = useCallback(() => {
    setTranscripts([]);
  }, []);

  // Connect to WebSocket
  const connect = useCallback((voiceName?: string) => {
    if (wsRef.current) return;

    setStatus('connecting');
    setError(null);

    const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8080';
    const voiceParam = voiceName ? `?voice=${encodeURIComponent(voiceName)}` : '';
    const ws = new WebSocket(`${wsUrl}/ws/${userIdRef.current}/${sessionIdRef.current}${voiceParam}`);
    ws.binaryType = 'arraybuffer';

    ws.addEventListener('open', () => {
      setStatus('connected');
      setError(null);
    });

    ws.addEventListener('message', (event) => {
      if (event.data instanceof ArrayBuffer) {
        playAudio(event.data);
      } else {
        try {
          const data = JSON.parse(event.data);
          handleJsonMessage(data);
        } catch (e) {
          console.error('Failed to parse message:', e);
        }
      }
    });

    ws.addEventListener('close', () => {
      setStatus('disconnected');
      wsRef.current = null;
    });

    ws.addEventListener('error', () => {
      setStatus('error');
      setError('WebSocket connection error');
    });

    wsRef.current = ws;
  }, [playAudio, handleJsonMessage]);

  // Disconnect
  const disconnect = useCallback(() => {
    stopRecording();
    stopVideo();
    resetPlayback();
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setStatus('disconnected');
  }, [resetPlayback]);

  // Start recording
  const startRecording = useCallback(async () => {
    if (isRecording || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return;
    }

    try {
      captureCtxRef.current = new AudioContext({ sampleRate: 16000 });
      mediaStreamRef.current = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
      });

      const source = captureCtxRef.current.createMediaStreamSource(mediaStreamRef.current);

      // Create worklet from blob
      const blob = new Blob([PCM_PROCESSOR_CODE], { type: 'application/javascript' });
      const workletUrl = URL.createObjectURL(blob);
      await captureCtxRef.current.audioWorklet.addModule(workletUrl);
      URL.revokeObjectURL(workletUrl);

      workletNodeRef.current = new AudioWorkletNode(captureCtxRef.current, 'pcm-capture');
      workletNodeRef.current.port.onmessage = (e) => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(e.data);
        }
      };

      // Keep audio graph alive without playing mic back
      const silentGain = captureCtxRef.current.createGain();
      silentGain.gain.value = 0;
      source.connect(workletNodeRef.current);
      workletNodeRef.current.connect(silentGain);
      silentGain.connect(captureCtxRef.current.destination);

      setIsRecording(true);
      setError(null);
    } catch (err: any) {
      setError(`Microphone error: ${err.message}`);
    }
  }, [isRecording]);

  // Stop recording
  const stopRecording = useCallback(() => {
    if (!isRecording) return;

    if (workletNodeRef.current) {
      workletNodeRef.current.disconnect();
      workletNodeRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((t) => t.stop());
      mediaStreamRef.current = null;
    }
    if (captureCtxRef.current) {
      captureCtxRef.current.close();
      captureCtxRef.current = null;
    }

    setIsRecording(false);
  }, [isRecording]);

  // Capture video frame
  const captureVideoFrame = useCallback(() => {
    if (!videoElementRef.current || !videoCanvasRef.current || 
        !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return;
    }

    const video = videoElementRef.current;
    const vw = video.videoWidth;
    const vh = video.videoHeight;
    if (!vw || !vh) return;

    const scale = Math.min(1, VIDEO_MAX_DIM / Math.max(vw, vh));
    const w = Math.round(vw * scale);
    const h = Math.round(vh * scale);

    videoCanvasRef.current.width = w;
    videoCanvasRef.current.height = h;
    const ctx = videoCanvasRef.current.getContext('2d');
    if (!ctx) return;

    ctx.drawImage(video, 0, 0, w, h);

    const frameDataUrl = videoCanvasRef.current.toDataURL('image/jpeg', VIDEO_JPEG_QUALITY);
    const base64Data = frameDataUrl.split(',')[1];
    if (!base64Data || base64Data.length < 100) return;

    wsRef.current.send(JSON.stringify({
      type: 'video_frame',
      data: base64Data,
      mimeType: 'image/jpeg',
    }));
  }, []);

  // Start video - accepts an existing MediaStream to reuse
  const startVideo = useCallback(async (existingStream?: MediaStream) => {
    if (isVideoOn || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return;
    }

    try {
      // Use existing stream if provided, otherwise create new one
      if (existingStream) {
        videoStreamRef.current = existingStream;
        ownsVideoStreamRef.current = false;
      } else {
        videoStreamRef.current = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 768 },
            height: { ideal: 768 },
            facingMode: 'user',
          }
        });
        ownsVideoStreamRef.current = true;
      }

      // Create hidden video element for capture
      videoElementRef.current = document.createElement('video');
      videoElementRef.current.srcObject = videoStreamRef.current;
      videoElementRef.current.muted = true;
      videoElementRef.current.playsInline = true;
      await videoElementRef.current.play();

      videoCanvasRef.current = document.createElement('canvas');

      setIsVideoOn(true);
      setError(null);

      // Start frame capture interval
      videoTimerRef.current = window.setInterval(captureVideoFrame, VIDEO_FRAME_INTERVAL_MS);
      captureVideoFrame(); // Capture first frame immediately
    } catch (err: any) {
      setError(`Video error: ${err.message}`);
    }
  }, [isVideoOn, captureVideoFrame]);

  // Track if we own the video stream (created it ourselves)
  const ownsVideoStreamRef = useRef(false);

  // Stop video
  const stopVideo = useCallback(() => {
    if (!isVideoOn) return;

    if (videoTimerRef.current) {
      clearInterval(videoTimerRef.current);
      videoTimerRef.current = null;
    }
    // Only stop tracks if we created the stream ourselves
    if (videoStreamRef.current && ownsVideoStreamRef.current) {
      videoStreamRef.current.getTracks().forEach((t) => t.stop());
    }
    videoStreamRef.current = null;
    ownsVideoStreamRef.current = false;
    if (videoElementRef.current) {
      videoElementRef.current.srcObject = null;
      videoElementRef.current = null;
    }
    videoCanvasRef.current = null;

    setIsVideoOn(false);
  }, [isVideoOn]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    isConnected: status === 'connected',
    isRecording,
    status,
    connect,
    disconnect,
    startRecording,
    stopRecording,
    startVideo,
    stopVideo,
    isVideoOn,
    error,
    transcripts,
    clearTranscripts,
  };
};