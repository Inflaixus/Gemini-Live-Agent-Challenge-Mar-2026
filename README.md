# Dental Trainer - Gemini Live Agent Challenge March 2026
## Description
We are developing a Live AI Agent that simulates a dental patient encounter to help postgraduate dentists prepare for fellowship and clinical examinations. The system allows dentists to practice history taking, patient assessment, clinical decision-making, consultation, and diagnosis in a realistic exam-like scenario. This interactive training environment helps clinicians strengthen their clinical reasoning and communication skills before their actual exams.

## Architecture Diagram 
Our architecture leverages the Google ADK Framework on Cloud Run to bridge Gemini Live's real-time voice capabilities with a custom two-tier RAG pipeline for grounded dental Dental simulations  

<p align="center">
  <img src="assets/Solution Architecture.png" width="100%">
</p>

## Demo Video & Cloud Proof Video
Cloud Proof Video:  https://drive.google.com/file/d/174NSc1LWAkPQhqYgJEVuyw6Q6tQU_nXZ/view?usp=share_link
Demo Video: https://www.youtube.com/watch?v=zFzz619a3us
 
## Key Features
### 1. Real-Time Multimodal Stream (ADK + Live API)
Unlike standard REST APIs that send text back and forth,  architecture uses WebSockets. This allows for a continuous flow of PCM audio data.  

### 2. Affective Dialog & Persona Grounding
 System isn't robotic; it adapts its emotional tone.  
 Detail: By passing "Emotional Profile" as an injected context in engine.py, the Gemini 2.5 Flash model adjusts its vocabulary (e.g., "I'm worried" if the doctor is saying something to worry about). 

### 3. Silence Monitoring
After 5 sec. agent detect that no one is talking send a nudge to human if still there.  

### 4. Interuption Handling
Interuppt the agent and check stopping and preserving context.

### 5. Clinical Accuracy: 
Grounded in YAML knowledge bases (RAG).  

## Tech Stack & Google Cloud Usage.
### Core AI Engine
- LLM: Gemini 2.5 Flash (chosen for low latency and high grounding accuracy).  
- Framework: Google ADK (Agent Development Kit) for seamless Live API orchestration.  
- Embeddings: BAAI/bge-m3 (Multilingual) for robust English/Arabic retrieval.  
- Vector Store: FAISS (IndexFlatIP) for high-speed local similarity search.  
- Knowledge Base: Structured YAML-based Patient Case Files.

### Google Cloud & IaC
We codified our entire production environment using Terraform to ensure the simulation is repeatable, scalable, and secure.
Compute: Google Cloud Run – Hosts the ADK Agent and RAG pipeline in a stateless, auto-scaling container.
  
## Installation(How to run) & Testing Instructions
### Installation
URL to test the agent: https://bilingual-audio-agent-312968462669.us-central1.run.app

### Testing Instructions  
Sample of the scenarios path in repo: Test Scenarios Folder

## User Interface Details
The experience starts with a welcoming Introduction Screen that explains the simulator's purpose and lists the clinical skills students will practice. From there, students select from available OSCE stations on the Scenario Selection screen, where scenarios are randomly assigned to simulate real exam conditions.

The main Virtual Patient Screen is where the magic happens. Students interact with an AI-powered patient through real-time voice conversation. Key features include:

- Voice persona selection with different patient personalities and voices
- Live audio streaming with visual feedback showing when the AI is listening
- Optional camera preview for video-enabled sessions
- A countdown timer extracted from scenario instructions with audio warnings
- A collapsible sidebar with two tabs: the Candidate Brief (patient details, scenario context, and tasks) and a live Transcript of the conversation
- A notes section for students to write down clinical observations during the session

The interface provides clear status indicators for connection state, microphone activity, and video streaming. Sound effects give feedback when sessions start/stop, and toast notifications keep users informed. The whole experience is responsive and works across different screen sizes.


## Challenges & Future Roadmap.  
- Roll-out to a lot of scenarios to create an actual program.
- Fine-tuning the model specifically on dental terminology.
- Adding a visual layer where the "patient" shows their teeth via Gemini's multimodal capabilities.
