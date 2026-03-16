import React, { useMemo } from 'react';
import { HashRouter as Router, Routes, Route, useNavigate } from 'react-router-dom';
import { Sparkles, ClipboardList, ArrowLeft, Loader2, AlertTriangle } from 'lucide-react';
import { ScenarioProvider, useScenario } from './context/ScenarioContext';
import { useScenarios } from './hooks/useScenarios';
import { ScenarioCard } from './components/ScenarioCard';
import { VirtualPatientScreen } from './components/VirtualPatientScreen';
import { IntroductionScreen } from './components/IntroductionScreen';
import { Scenario } from './types';

const HomeScreen: React.FC = () => {
  const { selectScenario } = useScenario();
  const navigate = useNavigate();
  const { scenarios, loading, error } = useScenarios();

  // Grouping Logic
  const groupedScenarios = useMemo(() => {
    const groups: Record<string, Scenario[]> = {};
    scenarios.forEach(scenario => {
      if (!groups[scenario.groupName]) {
        groups[scenario.groupName] = [];
      }
      groups[scenario.groupName].push(scenario);
    });
    return groups;
  }, [scenarios]);

  const scenarioGroups = Object.keys(groupedScenarios);

  const handleGroupSelect = (groupName: string, index: number) => {
    const group = groupedScenarios[groupName];
    if (group && group.length > 0) {
      // Test Mode: Randomly select one specific scenario variation
      // This ensures the student doesn't know exactly what 'type' of patient they will get (e.g. Angry vs Anxious)
      const randomIndex = Math.floor(Math.random() * group.length);
      const selectedVariant = group[randomIndex];

      // Mask details for the test environment
      const testScenario: Scenario = {
        ...selectedVariant,
        groupName: `Scenario ${index + 1}`, // Generic Header
        title: `Station ${index + 1}`, // Generic Title
        // Description is kept for internal logic if needed, but UI will hide it
      };
      
      selectScenario(testScenario);
      navigate('/scenario');
    }
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

      {/* Back Button */}
      <button 
        onClick={() => navigate('/')}
        className="fixed top-6 left-6 z-20 p-3 bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 rounded-xl text-slate-400 hover:text-white transition-all duration-300 backdrop-blur-sm"
        title="Back to Introduction"
      >
        <ArrowLeft className="w-5 h-5" />
      </button>

      <div className="absolute text-4xl opacity-[0.07]" style={{ animation: 'floatAround1 25s ease-in-out infinite' }}>🦷</div>
      <div className="absolute text-2xl opacity-[0.07]" style={{ animation: 'floatAround2 30s ease-in-out infinite' }}>🪥</div>
      <div className="absolute text-3xl opacity-[0.07]" style={{ animation: 'floatAround3 28s ease-in-out infinite' }}>💉</div>
      <div className="absolute text-xl opacity-[0.07]" style={{ animation: 'floatAround4 32s ease-in-out infinite' }}>🦷</div>
      <div className="absolute text-5xl opacity-[0.07]" style={{ animation: 'floatAround5 27s ease-in-out infinite' }}>🩺</div>
      <div className="absolute text-xl opacity-[0.07]" style={{ animation: 'floatAround6 35s ease-in-out infinite' }}>💊</div>

      {/* Header Hero */}
      <div className="relative z-10 pt-16 pb-8 px-4 sm:px-6 lg:px-8 text-center transition-all duration-500">
        
        <div className="flex flex-col items-center">
          {/* Logo Replacement */}
          <div className="mb-8 p-1 relative group">
            <div className="absolute inset-0 bg-medical-500 blur-xl opacity-20 group-hover:opacity-40 transition-opacity duration-500 rounded-full animate-pulse"></div>
            <div className="relative w-24 h-24 rounded-full bg-gradient-to-tr from-slate-900 to-slate-800 border border-white/10 flex items-center justify-center shadow-2xl backdrop-blur-sm">
              <ClipboardList className="w-12 h-12 text-medical-400 drop-shadow-[0_0_10px_rgba(167,139,250,0.5)]" />
            </div>
          </div>

          <h1 className="text-4xl md:text-6xl font-bold text-white tracking-tight mb-4 drop-shadow-md">
            Trainer Examination
          </h1>
          <p className="text-lg md:text-xl text-slate-300 max-w-2xl mx-auto leading-relaxed">
            Select a station to begin your assessment. Patient details will be provided inside.
          </p>
        </div>
      </div>

      {/* Grid */}
      <main className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-grow w-full">
        {/* Loading State */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-20">
            <Loader2 className="w-12 h-12 text-medical-400 animate-spin mb-4" />
            <p className="text-slate-400">Loading scenarios...</p>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="flex flex-col items-center justify-center py-20">
            <div className="bg-red-500/10 border border-red-500/20 rounded-2xl p-8 text-center max-w-md">
              <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-white mb-2">Failed to Load Scenarios</h3>
              <p className="text-slate-400 mb-4">{error}</p>
              <p className="text-slate-500 text-sm">Make sure the backend server is running on port 8080</p>
            </div>
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && scenarioGroups.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20">
            <div className="bg-slate-800/50 border border-white/10 rounded-2xl p-8 text-center max-w-md">
              <ClipboardList className="w-12 h-12 text-slate-500 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-white mb-2">No Scenarios Available</h3>
              <p className="text-slate-400">No scenarios have been configured in the backend yet.</p>
            </div>
          </div>
        )}

        {/* Scenarios Grid */}
        {!loading && !error && scenarioGroups.length > 0 && (
          <div className={`grid gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500 ${
            scenarioGroups.length === 1 
              ? 'grid-cols-1 max-w-md mx-auto' 
              : 'grid-cols-1 md:grid-cols-2 lg:grid-cols-2'
          }`}>
            {scenarioGroups.map((groupName, index) => {
              const groupScenarios = groupedScenarios[groupName];
              return (
                <ScenarioCard 
                  key={groupName}
                  title={`Scenario ${index + 1}`}
                  category="OSCE Station"
                  description="Enter the simulation room to begin the clinical interview and assessment."
                  count={groupScenarios.length}
                  onClick={() => handleGroupSelect(groupName, index)}
                />
              );
            })}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="relative z-10 py-12 text-center border-t border-white/5 bg-black/20 backdrop-blur-sm mt-12">
        <div className="flex justify-center mb-6 items-center gap-2">
          <span className="text-xl font-bold tracking-[0.2em] text-slate-500">INFLAIXUS</span>
        </div>
        <p className="text-slate-500 text-sm">© {new Date().getFullYear()} Dental Trainer Simulator. Examination Mode.</p>
      </footer>
    </div>
  );
};

const App = () => {
  return (
    <ScenarioProvider>
      <Router>
        <Routes>
          <Route path="/" element={<IntroductionScreen />} />
          <Route path="/scenarios" element={<HomeScreen />} />
          <Route path="/scenario" element={<VirtualPatientScreen />} />
        </Routes>
      </Router>
    </ScenarioProvider>
  );
};

export default App;