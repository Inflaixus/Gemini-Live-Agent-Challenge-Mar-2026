/**
 * AudioWorklet processor – captures mic input as 16-bit PCM and posts
 * the raw bytes to the main thread via MessagePort.
 */
class PCMCaptureProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const input = inputs[0];
    if (input.length === 0) return true;

    const float32 = input[0]; // mono channel
    const pcm16 = new Int16Array(float32.length);
    for (let i = 0; i < float32.length; i++) {
      const s = Math.max(-1, Math.min(1, float32[i]));
      pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    this.port.postMessage(pcm16.buffer, [pcm16.buffer]);
    return true;
  }
}

registerProcessor("pcm-capture", PCMCaptureProcessor);
