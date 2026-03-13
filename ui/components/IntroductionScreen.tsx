import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Brain, ArrowRight, Sparkles } from 'lucide-react';

// Custom Tooth SVG Icon
const ToothIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 2C9.5 2 7 3.5 7 6.5C7 9 6 11 5 14C4 17 5 22 7.5 22C9 22 9.5 20 10.5 18C11 17 11.5 16.5 12 16.5C12.5 16.5 13 17 13.5 18C14.5 20 15 22 16.5 22C19 22 20 17 19 14C18 11 17 9 17 6.5C17 3.5 14.5 2 12 2Z" />
  </svg>
);

interface SkillItemProps {
  text: string;
}

const SkillItem: React.FC<SkillItemProps> = ({ text }) => (
  <div className="flex items-center gap-2 text-slate-300">
    <ToothIcon className="w-4 h-4 text-medical-400 flex-shrink-0" />
    <span className="text-sm">{text}</span>
  </div>
);

export const IntroductionScreen: React.FC = () => {
  const navigate = useNavigate();

  const handleStart = () => {
    navigate('/scenarios');
  };

  return (
    <div className="min-h-screen flex flex-col relative overflow-hidden text-white">
      {/* Background Image */}
      <div className="fixed inset-0 z-0">
        <img src="/Backgrounds-01.png" alt="" className="w-full h-full object-cover" />
        <div className="absolute inset-0 bg-black/30"></div>
      </div>

      {/* Floating Dental Emoji Decorations with movement */}
      <style>{`
        @keyframes floatAround1 {
          0% { top: 10%; left: 10%; }
          25% { top: 20%; left: 80%; }
          50% { top: 70%; left: 85%; }
          75% { top: 60%; left: 15%; }
          100% { top: 10%; left: 10%; }
        }
        @keyframes floatAround2 {
          0% { top: 20%; right: 15%; }
          25% { top: 60%; right: 70%; }
          50% { top: 80%; right: 20%; }
          75% { top: 40%; right: 5%; }
          100% { top: 20%; right: 15%; }
        }
        @keyframes floatAround3 {
          0% { bottom: 30%; left: 20%; }
          25% { bottom: 60%; left: 70%; }
          50% { bottom: 20%; left: 80%; }
          75% { bottom: 50%; left: 10%; }
          100% { bottom: 30%; left: 20%; }
        }
        @keyframes floatAround4 {
          0% { top: 50%; left: 5%; }
          25% { top: 15%; left: 50%; }
          50% { top: 30%; left: 90%; }
          75% { top: 70%; left: 60%; }
          100% { top: 50%; left: 5%; }
        }
        @keyframes floatAround5 {
          0% { bottom: 25%; right: 10%; }
          25% { bottom: 70%; right: 60%; }
          50% { bottom: 15%; right: 80%; }
          75% { bottom: 55%; right: 25%; }
          100% { bottom: 25%; right: 10%; }
        }
        @keyframes floatAround6 {
          0% { top: 15%; right: 5%; }
          25% { top: 55%; right: 45%; }
          50% { top: 75%; right: 75%; }
          75% { top: 35%; right: 15%; }
          100% { top: 15%; right: 5%; }
        }
      `}</style>
      <div className="absolute text-4xl opacity-[0.07]" style={{ animation: 'floatAround1 25s ease-in-out infinite' }}>🦷</div>
      <div className="absolute text-2xl opacity-[0.07]" style={{ animation: 'floatAround2 30s ease-in-out infinite' }}>🪥</div>
      <div className="absolute text-3xl opacity-[0.07]" style={{ animation: 'floatAround3 28s ease-in-out infinite' }}>💉</div>
      <div className="absolute text-xl opacity-[0.07]" style={{ animation: 'floatAround4 32s ease-in-out infinite' }}>🦷</div>
      <div className="absolute text-5xl opacity-[0.07]" style={{ animation: 'floatAround5 27s ease-in-out infinite' }}>🩺</div>
      <div className="absolute text-xl opacity-[0.07]" style={{ animation: 'floatAround6 35s ease-in-out infinite' }}>💊</div>

      {/* Top Header with Company Name */}
      <header className="relative z-10 px-6 py-4">
        <div className="flex items-center gap-2">
          <span className="text-sm font-bold tracking-[0.3em] text-slate-400">INFLAIXUS</span>
        </div>
      </header>

      {/* Main Content */}
      <main className="relative z-10 flex-grow flex flex-col items-center justify-center px-4 sm:px-6 lg:px-8 py-8">
        
        <div className="max-w-3xl w-full text-center space-y-10">
          
          {/* Logo & Title */}
          <div className="space-y-6">
            <style>{`
              @keyframes rotate3d {
                0% { transform: perspective(500px) rotateY(0deg); }
                100% { transform: perspective(500px) rotateY(360deg); }
              }
            `}</style>
            <div className="flex justify-center">
              <div className="relative group">
                <div className="absolute inset-0 bg-medical-500 blur-xl opacity-30 group-hover:opacity-50 transition-opacity duration-500 rounded-full animate-pulse"></div>
                <div className="absolute -inset-2 bg-gradient-to-r from-medical-500 via-purple-500 to-medical-500 rounded-full opacity-20 blur-md group-hover:opacity-30 transition-opacity duration-500"></div>
                <div className="relative w-28 h-28 rounded-full bg-gradient-to-br from-slate-800 via-slate-900 to-slate-950 border-2 border-medical-500/30 flex items-center justify-center shadow-2xl">
                  <span 
                    className="text-6xl drop-shadow-[0_0_20px_rgba(167,139,250,0.6)] filter saturate-150"
                    style={{ animation: 'rotate3d 4s linear infinite', transformStyle: 'preserve-3d' }}
                  >🦷</span>
                </div>
              </div>
            </div>

            <div>
              <h1 className="text-4xl md:text-5xl font-bold text-white tracking-tight mb-4 drop-shadow-md">
                Dental Trainer Simulator
              </h1>
              <p className="text-lg text-slate-300 max-w-xl mx-auto leading-relaxed">
                Master your clinical communication skills for BDS examinations with AI-powered virtual dental patients.
              </p>
            </div>
          </div>

          {/* About Section */}
          <div className="bg-slate-800/20 backdrop-blur-sm rounded-2xl border border-white/5 p-6 text-left">
            <h2 className="text-lg font-semibold text-white mb-3">What is this?</h2>
            <p className="text-slate-300 leading-relaxed">
              This is an AI-powered Trainer examination simulator designed for dental students. 
              Practice clinical scenarios with virtual patients who respond realistically to your questions. 
              Each station presents a unique case where you'll take patient histories, discuss treatment options, 
              and manage complex situations — just like in a real dentail exam.
            </p>
          </div>

          {/* What You'll Practice Section */}
          <div className="bg-slate-800/20 backdrop-blur-sm rounded-2xl border border-white/5 p-6">
            <div className="flex items-center justify-center gap-2 mb-4">
              <Brain className="w-5 h-5 text-medical-400" />
              <h2 className="text-lg font-semibold text-white">What You'll Practice</h2>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              <SkillItem text="Patient History Taking" />
              <SkillItem text="Clinical Communication" />
              <SkillItem text="Treatment Discussion" />
              <SkillItem text="Complex Case Management" />
              <SkillItem text="Oral Medicine Cases" />
              <SkillItem text="Extraction Consent" />
              <SkillItem text="Restorative Options" />
              <SkillItem text="Patient Anxiety Management" />
              <SkillItem text="Medical History Review" />
            </div>
          </div>

          {/* Start Button */}
          <div className="pt-2">
            <button
              onClick={handleStart}
              className="group inline-flex items-center gap-3 px-8 py-4 bg-medical-600 hover:bg-medical-500 text-white font-semibold text-lg rounded-full shadow-lg shadow-medical-500/25 hover:shadow-medical-500/40 transition-all duration-300 ring-4 ring-medical-500/20 hover:ring-medical-500/30"
            >
              Start Examination
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </button>
            <p className="mt-4 text-slate-500 text-sm">
              Designed for dental students preparing for exams
            </p>
          </div>

        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 py-6 text-center border-t border-white/5 bg-black/20 backdrop-blur-sm">
        <p className="text-slate-500 text-xs">© {new Date().getFullYear()} Dental Trainer Simulator. All rights reserved.</p>
      </footer>
    </div>
  );
};
