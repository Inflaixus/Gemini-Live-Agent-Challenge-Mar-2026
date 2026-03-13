import React from 'react';
import { ArrowRight, Activity, AlertCircle, MessageCircle } from 'lucide-react';

interface SelectionCardProps {
  title: string;
  category: string;
  description: string;
  onClick: () => void;
  count?: number; // Kept as optional prop to avoid breaking changes if passed, but not used.
}

export const ScenarioCard: React.FC<SelectionCardProps> = ({ 
  title, 
  category, 
  description, 
  onClick,
}) => {
  const getIcon = (cat: string) => {
    switch (cat) {
      case 'Oral Medicine': return <Activity className="w-5 h-5 text-blue-400" />;
      case 'Conflict Resolution': return <AlertCircle className="w-5 h-5 text-red-400" />;
      case 'Communication': return <MessageCircle className="w-5 h-5 text-purple-400" />;
      default: return <Activity className="w-5 h-5 text-medical-400" />;
    }
  };

  return (
    <div 
      className="bg-slate-800/40 backdrop-blur-md rounded-2xl border border-white/10 p-6 hover:bg-slate-800/60 hover:border-medical-500/50 hover:shadow-[0_0_20px_rgba(139,92,246,0.3)] transition-all duration-300 cursor-pointer flex flex-col h-full group relative overflow-hidden"
      onClick={onClick}
    >
      {/* Inner glow effect on hover */}
      <div className="absolute inset-0 bg-gradient-to-br from-medical-500/0 to-medical-500/0 group-hover:from-medical-500/10 group-hover:to-transparent transition-all duration-500"></div>

      <div className="relative z-10">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-white/5 border border-white/5">
              {getIcon(category)}
            </div>
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">{category}</span>
          </div>
        </div>
        
        <h3 className="text-xl font-bold text-white mb-3 group-hover:text-medical-300 transition-colors">
          {title}
        </h3>
        
        <p className="text-slate-300 text-sm mb-6 leading-relaxed">
          {description}
        </p>
      </div>

      <div className="mt-auto pt-4 border-t border-white/10 flex items-center justify-end relative z-10">
        <button 
          className="text-sm font-semibold text-medical-400 flex items-center gap-1 group-hover:gap-2 transition-all group-hover:text-medical-300"
        >
          Start Practice <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};