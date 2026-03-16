import React, { useState, useEffect, useCallback, useRef } from 'react';
import { ArrowLeft, Mic, MicOff, User, Info, AlertTriangle, FileText, Clipboard, Check, PanelRightClose, PanelRightOpen, Video, VideoOff, Clock, X, Wifi, WifiOff } from 'lucide-react';
import { useScenario } from '../context/ScenarioContext';
import { useLiveAgent } from '../hooks/useLiveAgent';
import { useNavigate } from 'react-router-dom';

export const VirtualPatientScreen: React.FC = () => {
  const { selectedScenario, clearScenario } = useScenario();
  const navigate = useNavigate();
  const { 
    isConnected,
    isRecording,
    isVideoOn,
    connect,
    disconnect,
    startRecording,
    stopRecording,
    startVideo,
    stopVideo,
    error: agentError 
  } = useLiveAgent();
  
  const [showInfo, setShowInfo] = useState(true); // Toggle for sidebar - default open
  const [userNotes, setUserNotes] = useState(''); // State for user clinical notes
  const [notification, setNotification] = useState<{ message: string; type: 'start' | 'stop' } | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true); // Sidebar toggle for desktop - default open
  const [cameraOn, setCameraOn] = useState(false); // Camera state
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null); // Camera stream
  const [cameraError, setCameraError] = useState<string | null>(null); // Camera error state
  const videoRef = useRef<HTMLVideoElement>(null); // Video element ref
  const [timeLeft, setTimeLeft] = useState<number>(0); // Timer in seconds
  const [timerStarted, setTimerStarted] = useState(false); // Timer started flag
  const [selectedPersona, setSelectedPersona] = useState<string | null>(null); // Selected AI persona
  const warningPlayedRef = useRef(false); // Track if warning sound was played

  // Extract time from instructions (e.g., "You have 8 minutes.")
  const getTimerDuration = useCallback(() => {
    if (!selectedScenario?.brief?.instructions) return 8 * 60; // Default 8 minutes
    
    for (const instruction of selectedScenario.brief.instructions) {
      const match = instruction.match(/(\d+)\s*minutes?/i);
      if (match) {
        return parseInt(match[1]) * 60; // Convert to seconds
      }
    }
    return 8 * 60; // Default 8 minutes if not found
  }, [selectedScenario]);

  // Initialize timer when scenario loads
  useEffect(() => {
    if (selectedScenario && !timerStarted) {
      const duration = getTimerDuration();
      setTimeLeft(duration);
      setTimerStarted(true);
      warningPlayedRef.current = false;
    }
  }, [selectedScenario, timerStarted, getTimerDuration]);

  // Timer countdown
  useEffect(() => {
    if (!timerStarted || timeLeft <= 0) return;

    const interval = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [timerStarted, timeLeft]);

  // Format time as MM:SS
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Warning sound when 1 minute left
  const playWarningSound = useCallback(() => {
    try {
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      
      // Play 3 beeps
      for (let i = 0; i < 3; i++) {
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.setValueAtTime(800, audioContext.currentTime + i * 0.3);
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime + i * 0.3);
        gainNode.gain.linearRampToValueAtTime(0, audioContext.currentTime + i * 0.3 + 0.15);
        
        oscillator.start(audioContext.currentTime + i * 0.3);
        oscillator.stop(audioContext.currentTime + i * 0.3 + 0.15);
      }
    } catch (e) {
      console.log('Audio not supported');
    }
  }, []);

  // Check for warning time (1 minute left)
  useEffect(() => {
    if (timeLeft === 60 && !warningPlayedRef.current) {
      playWarningSound();
      warningPlayedRef.current = true;
    }
  }, [timeLeft, playWarningSound]);

  // Sound effect function using Web Audio API
  const playSound = useCallback((type: 'start' | 'stop') => {
    try {
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      
      if (type === 'start') {
        // Rising tone for start
        oscillator.frequency.setValueAtTime(400, audioContext.currentTime);
        oscillator.frequency.linearRampToValueAtTime(600, audioContext.currentTime + 0.15);
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.linearRampToValueAtTime(0, audioContext.currentTime + 0.2);
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.2);
      } else {
        // Falling tone for stop
        oscillator.frequency.setValueAtTime(500, audioContext.currentTime);
        oscillator.frequency.linearRampToValueAtTime(300, audioContext.currentTime + 0.15);
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.linearRampToValueAtTime(0, audioContext.currentTime + 0.2);
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.2);
      }
    } catch (e) {
      console.log('Audio not supported');
    }
  }, []);

  // Show notification function
  const showNotification = useCallback((message: string, type: 'start' | 'stop') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 2500);
  }, []);

  // Camera sound effect function
  const playCameraSound = useCallback((type: 'start' | 'stop') => {
    try {
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      
      if (type === 'start') {
        // Double beep for camera on (higher pitch)
        oscillator.frequency.setValueAtTime(700, audioContext.currentTime);
        oscillator.frequency.setValueAtTime(900, audioContext.currentTime + 0.1);
        gainNode.gain.setValueAtTime(0.25, audioContext.currentTime);
        gainNode.gain.linearRampToValueAtTime(0, audioContext.currentTime + 0.08);
        gainNode.gain.setValueAtTime(0.25, audioContext.currentTime + 0.1);
        gainNode.gain.linearRampToValueAtTime(0, audioContext.currentTime + 0.18);
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.2);
      } else {
        // Single low beep for camera off
        oscillator.frequency.setValueAtTime(400, audioContext.currentTime);
        gainNode.gain.setValueAtTime(0.25, audioContext.currentTime);
        gainNode.gain.linearRampToValueAtTime(0, audioContext.currentTime + 0.12);
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.12);
      }
    } catch (e) {
      console.log('Audio not supported');
    }
  }, []);

  // Toggle camera function
  const toggleCamera = useCallback(async () => {
    if (cameraOn) {
      // Stop video streaming first if active
      if (isVideoOn) {
        stopVideo();
      }
      // Stop camera
      if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        setCameraStream(null);
      }
      setCameraOn(false);
      setCameraError(null);
      playCameraSound('stop');
    } else {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        setCameraStream(stream);
        setCameraOn(true);
        setCameraError(null);
        playCameraSound('start');
        // If already recording, start video streaming
        if (isRecording && isConnected) {
          startVideo(stream);
        }
      } catch (err) {
        setCameraError('Camera permission denied');
        setCameraOn(false);
      }
    }
  }, [cameraOn, cameraStream, playCameraSound, isRecording, isConnected, isVideoOn, startVideo, stopVideo]);

  // Connect video element to stream
  useEffect(() => {
    if (videoRef.current && cameraStream) {
      videoRef.current.srcObject = cameraStream;
    }
  }, [cameraStream]);

  // Safety check if user lands here without selection
  useEffect(() => {
    if (!selectedScenario) {
      navigate('/scenarios');
    }
  }, [selectedScenario, navigate]);

  if (!selectedScenario) return null;

  // Determine patient gender and available personas with actual Gemini voice names
  const patientGender = selectedScenario.patientProfile?.gender?.toLowerCase();
  const isMale = patientGender === 'male';
  
  const personas = isMale ? [
    { id: 'male1', name: 'Ahmed', emoji: '👨🏼', voice: 'Deep & Calm', voiceName: 'Orus' },
    { id: 'male2', name: 'Omar', emoji: '👨🏻', voice: 'Friendly & Warm', voiceName: 'Puck' }
  ] : [
    { id: 'female1', name: 'Sara', emoji: '👩🏻', voice: 'Soft & Professional', voiceName: 'Aoede' },
    { id: 'female2', name: 'Nour', emoji: '👩🏽', voice: 'Gentle & Caring', voiceName: 'Kore' }
  ];

  const handleBack = () => {
    stopRecording();
    stopVideo();
    disconnect();
    clearScenario();
  };

  const toggleSession = async () => {
    if (isRecording) {
      stopRecording();
      if (cameraOn && cameraStream) {
        stopVideo();
      }
      playSound('stop');
      showNotification('Session ended', 'stop');
    } else {
      // Get the selected persona's voice name
      const selectedVoiceName = personas.find(p => p.id === selectedPersona)?.voiceName;
      
      // Connect WebSocket first if not connected
      if (!isConnected) {
        connect(selectedVoiceName);
      }
      // Wait a bit for connection then start recording
      setTimeout(async () => {
        await startRecording();
        // If camera is already on, start video streaming
        if (cameraOn && cameraStream) {
          startVideo(cameraStream);
        }
        playSound('start');
        showNotification('Session started', 'start');
      }, 500);
    }
  };

  return (
    <div className="h-screen w-full flex flex-col md:flex-row overflow-hidden text-white relative">
      
      {/* Notification Toast */}
      {notification && (
        <div className={`
          fixed top-6 left-1/2 -translate-x-1/2 z-50 
          animate-in fade-in slide-in-from-top-4 duration-300
        `}>
          <div className={`
            flex items-center gap-3 px-5 py-3 rounded-full shadow-2xl backdrop-blur-md border
            ${notification.type === 'start' 
              ? 'bg-emerald-500/20 border-emerald-500/30 text-emerald-300' 
              : 'bg-slate-700/80 border-slate-600/50 text-slate-300'}
          `}>
            <div className={`
              w-8 h-8 rounded-full flex items-center justify-center
              ${notification.type === 'start' ? 'bg-emerald-500/30' : 'bg-slate-600/50'}
            `}>
              {notification.type === 'start' 
                ? <Mic className="w-4 h-4" /> 
                : <MicOff className="w-4 h-4" />}
            </div>
            <span className="font-medium text-sm">{notification.message}</span>
            {notification.type === 'start' && (
              <Check className="w-4 h-4 text-emerald-400" />
            )}
          </div>
        </div>
      )}
      
      {/* Background Image */}
      <div className="absolute inset-0 z-0">
        <img src="/Backgrounds-01.png" alt="" className="w-full h-full object-cover" />
        <div className="absolute inset-0 bg-black/40"></div>
      </div>

      {/* Camera Preview Popup */}
      {cameraOn && cameraStream && (
        <div className="fixed bottom-32 left-6 z-40 animate-in fade-in slide-in-from-left-4 duration-300">
          <div className="relative bg-slate-900/90 backdrop-blur-xl rounded-2xl border border-white/10 shadow-2xl overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-3 py-2 bg-black/40 border-b border-white/10">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></div>
                <span className="text-xs font-medium text-slate-300">Camera Preview</span>
              </div>
              <button 
                onClick={toggleCamera}
                className="p-1 hover:bg-white/10 rounded-lg transition-colors"
                title="Close camera"
              >
                <X className="w-4 h-4 text-slate-400 hover:text-white" />
              </button>
            </div>
            {/* Video */}
            <video 
              ref={videoRef}
              autoPlay 
              playsInline 
              muted
              className="w-64 h-48 object-cover"
            />
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-full relative z-10 backdrop-blur-none">
        
        {/* Header */}
        <header className="bg-black/20 backdrop-blur-md border-b border-white/5 px-6 py-4 flex items-center justify-between z-20">
          <div className="flex items-center gap-4">
            <button 
              onClick={handleBack}
              className="p-2 hover:bg-white/10 rounded-full text-slate-300 hover:text-white transition-colors"
              title="Return to scenarios"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-xl font-bold text-white leading-tight">
                {selectedScenario.groupName}
              </h1>
            </div>
          </div>
          
          {/* Timer Display */}
          <div className={`
            flex items-center gap-2 px-4 py-2 rounded-xl font-mono text-lg font-bold transition-all duration-300
            ${timeLeft <= 60 
              ? 'bg-red-500/20 text-red-400 border border-red-500/30 animate-pulse' 
              : timeLeft <= 120 
                ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' 
                : 'bg-slate-800/60 text-white border border-white/10'}
          `}>
            <Clock className={`w-5 h-5 ${timeLeft <= 60 ? 'text-red-400' : timeLeft <= 120 ? 'text-amber-400' : 'text-medical-400'}`} />
            <span>{formatTime(timeLeft)}</span>
          </div>

          <div className="flex items-center gap-3">
             {/* Toggle Sidebar Button - Desktop */}
             <button 
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className={`
                  hidden md:flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium transition-all duration-300
                  ${sidebarOpen 
                    ? 'bg-medical-500/10 text-medical-300 border border-medical-500/20 hover:bg-medical-500/20' 
                    : 'bg-white/5 text-slate-400 border border-white/10 hover:bg-white/10 hover:text-white'}
                `}
                title={sidebarOpen ? "Hide panel" : "Show panel"}
             >
                {sidebarOpen ? (
                  <>
                    <PanelRightClose className="w-4 h-4" />
                    <span className="hidden lg:inline">Hide Brief</span>
                  </>
                ) : (
                  <>
                    <PanelRightOpen className="w-4 h-4" />
                    <span className="hidden lg:inline">Show Brief</span>
                  </>
                )}
             </button>

             
             {/* Toggle Sidebar Button - Mobile */}
             <button 
                onClick={() => setShowInfo(!showInfo)}
                className={`
                  md:hidden flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium transition-all duration-300
                  ${showInfo 
                    ? 'bg-medical-500/10 text-medical-300 border border-medical-500/20' 
                    : 'bg-white/5 text-slate-400 border border-white/10'}
                `}
             >
                <Info className="w-4 h-4" />
             </button>
          </div>
        </header>

        {/* Virtual Patient Viewport */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-8 flex flex-col items-center justify-center relative">
          
          <div className="max-w-2xl w-full text-center space-y-10 relative z-10">
            
            {/* Avatar Section */}
            <div className="flex items-center justify-center gap-12">
               {/* User Avatar (You) */}
               <div className="flex flex-col items-center gap-3 opacity-60">
                 <div className="w-20 h-20 rounded-full bg-slate-800 flex items-center justify-center border border-slate-700">
                    <User className="w-8 h-8 text-slate-400" />
                 </div>
                 <span className="text-sm font-medium text-slate-400">You</span>
               </div>

               {/* Patient/AI Avatar */}
               <div className="flex flex-col items-center gap-3">
                  <div className="relative">
                    <div className="w-28 h-28 bg-slate-800 rounded-full flex items-center justify-center border-2 border-slate-600 shadow-2xl relative z-10">
                      {selectedPersona ? (
                        <span className="text-5xl">{personas.find(p => p.id === selectedPersona)?.emoji}</span>
                      ) : (
                        <User className="w-12 h-12 text-medical-300" />
                      )}
                    </div>
                    {/* Animated Rings for AI */}
                    {isRecording && (
                      <>
                        <div className="absolute inset-0 rounded-full border border-medical-500/50 animate-[ping_2s_linear_infinite] opacity-50"></div>
                        <div className="absolute -inset-4 rounded-full border border-medical-500/30 animate-[ping_3s_linear_infinite] opacity-30"></div>
                      </>
                    )}
                  </div>
                  <span className="text-sm font-medium text-medical-300">
                    Patient: {selectedScenario.patientProfile.name}
                  </span>
               </div>
            </div>

            {/* Persona Selector */}
            {!selectedPersona && (
              <div className="bg-slate-800/40 backdrop-blur-sm rounded-2xl border border-white/10 p-6 max-w-md mx-auto">
                <h3 className="text-center text-white font-semibold mb-2">Select Patient Voice</h3>
                <p className="text-center text-slate-400 text-sm mb-4">Choose a persona for the AI patient</p>
                <div className="grid grid-cols-2 gap-3">
                  {personas.map((persona) => (
                    <button
                      key={persona.id}
                      onClick={() => setSelectedPersona(persona.id)}
                      className="group p-4 bg-white/5 hover:bg-medical-500/20 border border-white/10 hover:border-medical-500/40 rounded-xl transition-all duration-300"
                    >
                      <div className="text-4xl mb-2 group-hover:scale-110 transition-transform">{persona.emoji}</div>
                      <div className="text-white font-medium">{persona.name}</div>
                      <div className="text-slate-400 text-xs mt-1">{persona.voice}</div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Selected Persona Badge */}
            {selectedPersona && (
              <div className="flex justify-center">
                <div className="inline-flex items-center gap-3 px-4 py-2 bg-medical-500/10 border border-medical-500/20 rounded-full">
                  <span className="text-xl">{personas.find(p => p.id === selectedPersona)?.emoji}</span>
                  <span className="text-medical-300 text-sm font-medium">
                    Voice: {personas.find(p => p.id === selectedPersona)?.name}
                  </span>
                </div>
              </div>
            )}

            {/* Status Indicator */}
            <div className="space-y-6">
              <div className="h-8">
                <p className="text-slate-400 font-light tracking-wide text-sm uppercase">
                  {!isConnected && !isRecording && "Not Connected"}
                  {isConnected && !isRecording && <span className="text-blue-400">● Connected - Ready</span>}
                  {isRecording && <span className="text-medical-400 animate-pulse">● Listening...</span>}
                </p>
              </div>

              {/* Error Message */}
              {agentError && (
                <div className="bg-red-500/10 text-red-300 px-4 py-3 rounded-lg text-sm border border-red-500/20 inline-flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" />
                  {agentError}
                </div>
              )}
            </div>

          </div>
        </div>

        {/* Footer Controls */}
        <div className="bg-black/20 backdrop-blur-md border-t border-white/5 p-8 flex flex-col items-center justify-center relative z-20">
          
          {/* Action Buttons Row */}
          <div className="flex items-center gap-4">
            {/* Camera Button */}
            <button
              onClick={toggleCamera}
              className={`
                relative flex items-center justify-center w-14 h-14 rounded-full shadow-lg transition-all duration-300
                ${cameraOn 
                  ? 'bg-cyan-500 hover:bg-cyan-600 text-white ring-4 ring-cyan-500/20' 
                  : 'bg-slate-700/80 hover:bg-slate-600/80 text-slate-300 ring-4 ring-slate-500/10 hover:text-white'}
              `}
              title={cameraOn ? "Turn off camera" : "Turn on camera"}
            >
              {cameraOn ? <Video className="w-6 h-6" /> : <VideoOff className="w-6 h-6" />}
            </button>

            {/* Main Mic Button */}
            <button
              onClick={toggleSession}
              className={`
                relative flex items-center gap-3 px-8 py-4 rounded-full shadow-lg transition-all duration-300 font-semibold text-lg
                ${isRecording 
                  ? 'bg-red-500 hover:bg-red-600 text-white ring-4 ring-red-500/20' 
                  : 'bg-medical-600 hover:bg-medical-500 text-white ring-4 ring-medical-500/20 shadow-[0_0_30px_rgba(139,92,246,0.3)]'}
              `}
            >
              {isRecording ? (
                <>
                  <Mic className="w-6 h-6 animate-pulse" />
                  Stop Session
                </>
              ) : (
                <>
                  <Mic className="w-6 h-6" />
                  Start Session with Patient
                </>
              )}
            </button>
          </div>
          
          {/* Status Indicators */}
          <div className="mt-4 flex items-center gap-4 text-xs text-slate-500">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-slate-600'}`}></div>
              {isConnected ? 'Connected' : 'Disconnected'}
            </div>
            <span>•</span>
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${isRecording ? 'bg-green-500 animate-pulse' : 'bg-slate-600'}`}></div>
              {isRecording ? 'Microphone Active' : 'Microphone Ready'}
            </div>
            <span>•</span>
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${isVideoOn ? 'bg-cyan-500' : cameraOn ? 'bg-amber-500' : 'bg-slate-600'}`}></div>
              {isVideoOn ? 'Video Streaming' : cameraOn ? 'Camera On' : 'Camera Off'}
            </div>
            <span>•</span>
            <span>Powered by Inflaixus AI</span>
          </div>

          {/* Camera Error */}
          {cameraError && (
            <div className="mt-3 bg-red-500/10 text-red-300 px-4 py-2 rounded-lg text-xs border border-red-500/20 inline-flex items-center gap-2">
              <AlertTriangle className="w-3 h-3" />
              {cameraError}
            </div>
          )}
        </div>
      </div>

      {/* Sidebar Info Panel (Candidate Brief) */}
      <div className={`
        fixed inset-y-0 right-0 w-[420px] bg-gradient-to-b from-slate-900/98 via-slate-900/95 to-slate-950/98 backdrop-blur-2xl border-l border-white/10 shadow-2xl transform transition-all duration-300 z-30 overflow-y-auto
        md:relative md:shadow-[0_0_60px_rgba(0,0,0,0.5)] md:bg-gradient-to-b md:from-slate-900/40 md:via-slate-900/30 md:to-slate-950/40
        ${showInfo ? 'translate-x-0' : 'translate-x-full'}
        ${sidebarOpen ? 'md:translate-x-0 md:w-[420px] md:opacity-100' : 'md:translate-x-full md:w-0 md:opacity-0 md:overflow-hidden'}
      `}>
        {/* Decorative top gradient line */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-medical-500/50 to-transparent"></div>
        
        <div className="p-6 space-y-5">
          
          {/* Header with icon */}
          <div className="flex items-center gap-3 pb-4 border-b border-white/10">
            <div className="p-2.5 rounded-xl bg-medical-500/10 border border-medical-500/20">
              <Clipboard className="w-5 h-5 text-medical-400" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Candidate Brief</h2>
              <p className="text-xs text-slate-500">Review before starting</p>
            </div>
          </div>

          {/* Radiograph Image if available */}
          {selectedScenario.brief?.imageUrl && (
            <div className="rounded-xl overflow-hidden border border-white/10 bg-black/50 shadow-lg">
              <img 
                src={selectedScenario.brief.imageUrl} 
                alt="Radiograph" 
                className="w-full h-48 object-cover grayscale opacity-80 hover:opacity-100 transition-opacity"
              />
              <div className="bg-black/60 p-2.5 text-xs text-center text-slate-400 border-t border-white/10">
                Figure 1: Periapical Radiograph
              </div>
            </div>
          )}

          {/* Main Info Card */}
          <div className="bg-white/[0.03] p-5 rounded-2xl border border-white/10 space-y-4 text-sm shadow-inner backdrop-blur-sm">
            
            {/* Theme */}
            <div className="flex items-center gap-3">
              <div className="w-1 h-8 rounded-full bg-medical-500"></div>
              <div>
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block">Theme</span>
                <span className="font-semibold text-white text-base">{selectedScenario.title}</span>
              </div>
            </div>

            <div className="h-px bg-gradient-to-r from-transparent via-white/10 to-transparent"></div>

            {/* Patient Details */}
            <div>
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block mb-3">Patient Details</span>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-white/[0.03] rounded-lg p-3 border border-white/5">
                  <span className="text-slate-500 text-[10px] uppercase tracking-wider block mb-1">Name</span>
                  <span className="text-slate-200 font-medium">{selectedScenario.patientProfile.name}</span>
                </div>
                <div className="bg-white/[0.03] rounded-lg p-3 border border-white/5">
                  <span className="text-slate-500 text-[10px] uppercase tracking-wider block mb-1">Age</span>
                  <span className="text-slate-200 font-medium">{selectedScenario.patientProfile.age} years</span>
                </div>
                <div className="bg-white/[0.03] rounded-lg p-3 border border-white/5">
                  <span className="text-slate-500 text-[10px] uppercase tracking-wider block mb-1">Gender</span>
                  <span className="text-slate-200 font-medium">{selectedScenario.patientProfile.gender}</span>
                </div>
                {selectedScenario.patientProfile.occupation && (
                  <div className="bg-white/[0.03] rounded-lg p-3 border border-white/5">
                    <span className="text-slate-500 text-[10px] uppercase tracking-wider block mb-1">Occupation</span>
                    <span className="text-slate-200 font-medium">{selectedScenario.patientProfile.occupation}</span>
                  </div>
                )}
              </div>
            </div>

            <div className="h-px bg-gradient-to-r from-transparent via-white/10 to-transparent"></div>

            {/* Scenario Text */}
            <div>
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block mb-2">Scenario</span>
              <p className="text-slate-300 leading-relaxed">
                {selectedScenario.brief?.scenario || "Patient details are confidential. Please proceed with the examination."}
              </p>
            </div>

            {/* Task / At this station */}
            {selectedScenario.brief?.task && (
              <div className="bg-gradient-to-br from-medical-500/10 to-indigo-500/10 p-4 rounded-xl border border-medical-500/20 relative overflow-hidden">
                <div className="absolute top-0 right-0 w-20 h-20 bg-medical-500/10 rounded-full blur-2xl"></div>
                <span className="text-[10px] font-bold text-medical-300 uppercase tracking-widest block mb-2">At this station</span>
                <p className="text-white leading-relaxed font-medium relative z-10">
                  {selectedScenario.brief.task}
                </p>
              </div>
            )}

            {/* Instructions */}
            {selectedScenario.brief?.instructions && (
              <div>
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block mb-2">Instructions</span>
                <ul className="space-y-2">
                  {selectedScenario.brief.instructions.map((inst, i) => (
                    <li key={i} className="flex items-start gap-2 text-slate-300">
                      <span className="w-5 h-5 rounded-full bg-medical-500/20 text-medical-400 text-[10px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                        {i + 1}
                      </span>
                      <span>{inst}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Clinical Notes Input */}
          <div className="pt-3">
            <div className="flex items-center gap-2 mb-3">
              <FileText className="w-4 h-4 text-medical-400" />
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Your Notes</h3>
            </div>
            <div className="relative">
              <textarea 
                value={userNotes}
                onChange={(e) => setUserNotes(e.target.value)}
                placeholder="Type your clinical notes here..."
                className="w-full h-28 bg-white/[0.03] border border-white/10 rounded-xl p-4 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-medical-500/50 focus:border-medical-500/30 resize-none transition-all duration-300"
              />
            </div>
          </div>

          {/* End Session Button */}
          <button 
            onClick={handleBack}
            className="w-full py-3.5 px-4 bg-white/5 border border-white/10 text-slate-300 font-semibold rounded-xl hover:bg-red-500/10 hover:border-red-500/30 hover:text-red-300 transition-all duration-300"
          >
            End Session
          </button>

        </div>
      </div>
      
    </div>
  );
};