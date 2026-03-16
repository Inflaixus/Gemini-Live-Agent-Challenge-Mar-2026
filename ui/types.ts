export interface Scenario {
  id: string;
  title: string;
  groupName: string; // New field for grouping
  category: string;
  description: string; // Actor/Character description (Hidden from student)
  patientProfile: {
    name: string;
    age: number;
    gender: 'Male' | 'Female' | 'Other';
    medicalHistory: string;
    occupation?: string; // Added for brief
  };
  // New structure for the visible Candidate Brief
  brief?: {
    scenario: string;
    task: string;
    instructions: string[];
    imageUrl?: string;
  };
  goals: string[];
  clinicalNotes: string;
}

export type SpeechStatus = 'idle' | 'listening' | 'processing' | 'error';