import React, { createContext, useContext, useState, ReactNode } from 'react';
import { Scenario } from '../types';

interface ScenarioContextType {
  selectedScenario: Scenario | null;
  selectScenario: (scenario: Scenario) => void;
  clearScenario: () => void;
}

const ScenarioContext = createContext<ScenarioContextType | undefined>(undefined);

export const ScenarioProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [selectedScenario, setSelectedScenario] = useState<Scenario | null>(null);

  const selectScenario = (scenario: Scenario) => {
    setSelectedScenario(scenario);
  };

  const clearScenario = () => {
    setSelectedScenario(null);
  };

  return (
    <ScenarioContext.Provider value={{ selectedScenario, selectScenario, clearScenario }}>
      {children}
    </ScenarioContext.Provider>
  );
};

export const useScenario = () => {
  const context = useContext(ScenarioContext);
  if (context === undefined) {
    throw new Error('useScenario must be used within a ScenarioProvider');
  }
  return context;
};