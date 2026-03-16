import { useState, useEffect, useCallback, useRef } from 'react';
import { SpeechStatus } from '../types';

interface UseSpeechRecognitionReturn {
  isListening: boolean;
  transcript: string;
  status: SpeechStatus;
  startListening: () => void;
  stopListening: () => void;
  resetTranscript: () => void;
  error: string | null;
}

export const useSpeechRecognition = (): UseSpeechRecognitionReturn => {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [status, setStatus] = useState<SpeechStatus>('idle');
  const [error, setError] = useState<string | null>(null);
  
  // Use a ref to persist the recognition instance
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    // Check browser support
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
      setError('Browser does not support Speech Recognition.');
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      setIsListening(true);
      setStatus('listening');
      setError(null);
    };

    recognition.onresult = (event: any) => {
      let finalTranscript = '';
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript;
        }
      }
      if (finalTranscript) {
        setTranscript((prev) => prev + ' ' + finalTranscript);
      }
    };

    recognition.onerror = (event: any) => {
      // Handle 'no-speech' gracefully - it just means silence
      if (event.error === 'no-speech') {
        setIsListening(false);
        setStatus('idle');
        return;
      }

      if (event.error === 'aborted') {
        setIsListening(false);
        setStatus('idle');
        return;
      }

      console.warn('Speech recognition error:', event.error);

      if (event.error === 'not-allowed') {
         setError('Microphone permission denied. Please allow access.');
      } else if (event.error === 'network') {
         setError('Network error. A stable internet connection is required for voice recognition.');
      } else {
         setError(`Error: ${event.error}`);
      }
      setIsListening(false);
      setStatus('error');
    };

    recognition.onend = () => {
      setIsListening(false);
      // Only reset status to idle if we aren't in an error state
      setStatus((prevStatus) => prevStatus === 'error' ? 'error' : 'idle');
    };

    recognitionRef.current = recognition;

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, []); // Only run once on mount

  const startListening = useCallback(() => {
    if (recognitionRef.current && !isListening) {
      try {
        // Reset error on start
        setError(null); 
        recognitionRef.current.start();
      } catch (e) {
        console.error("Failed to start recognition:", e);
      }
    }
  }, [isListening]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current && isListening) {
      recognitionRef.current.stop();
      setStatus('processing'); // Transition to processing after speaking
    }
  }, [isListening]);

  const resetTranscript = useCallback(() => {
      setTranscript('');
      setStatus('idle');
      setError(null);
  }, []);

  return {
    isListening,
    transcript,
    status,
    startListening,
    stopListening,
    resetTranscript,
    error
  };
};