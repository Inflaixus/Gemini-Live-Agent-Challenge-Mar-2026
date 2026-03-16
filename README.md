# Dental Trainer - Gemini Live Agent Challenge March 2026
## Description
We are developing a Live AI Agent that simulates a dental patient encounter to help postgraduate dentists prepare for fellowship and clinical examinations. The system allows dentists to practice history taking, patient assessment, clinical decision-making, consultation, and diagnosis in a realistic exam-like scenario. This interactive training environment helps clinicians strengthen their clinical reasoning and communication skills before their actual exams.

## Architecture Diagram 
Our architecture leverages the Google ADK Framework on Cloud Run to bridge Gemini Live's real-time voice capabilities with a custom two-tier RAG pipeline for grounded dental Dental simulations  

<p align="center">
  <img src="assets/Solution Architecture.png" width="100%">
</p>

## Demo Video & Cloud Proof Video
Cloud Proof Video:  
Demo Video: 
 
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

## Challenges & Future Roadmap.  
- Roll-out to a lot of scenarios to create an actual program.
- Fine-tuning the model specifically on dental terminology.
- Adding a visual layer where the "patient" shows their teeth via Gemini's multimodal capabilities.
