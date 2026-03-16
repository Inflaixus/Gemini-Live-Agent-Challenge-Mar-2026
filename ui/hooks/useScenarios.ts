import { useState, useEffect } from 'react';
import { Scenario } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';

interface UseScenariosReturn {
  scenarios: Scenario[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export const useScenarios = (): UseScenariosReturn => {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchScenarios = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/scenarios`);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch scenarios: ${response.statusText}`);
      }
      
      const data = await response.json();
      setScenarios(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load scenarios');
      // Fallback to empty array
      setScenarios([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchScenarios();
  }, []);

  return {
    scenarios,
    loading,
    error,
    refetch: fetchScenarios,
  };
};
