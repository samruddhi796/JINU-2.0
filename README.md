# JINU 2.0 — AI Desktop Companion

A personal AI companion for CSE students built with Python, 
Groq LLaMA 3.3, FastAPI, and PyWebView.

## Features
- Real-time chat with LLaMA 3.3 70B via Groq API
- Environmental awareness — detects active apps and websites
- Screen vision — sees your screen when you ask questions  
- Voice input and output
- PC automation — open apps, control volume, set timers
- Long-term memory with ChromaDB vector search
- Permanent user profile that never forgets facts about you
- Proactive distraction warnings and study mode detection
- Animated desktop mascot (Week 4 — in progress)

## Tech Stack
Python · FastAPI · Groq API · PyWebView · SQLite · 
ChromaDB · SpeechRecognition · psutil · pygetwindow

## Setup
1. Clone the repo
2. Create `.env` file with your `GROQ_API_KEY`
3. `pip install -r requirements.txt`
4. `python main.py`

## Project Structure
- `backend/` — FastAPI server, AI brain, memory, watcher, task agent
- `frontend/` — Chat UI (HTML/CSS/JS)
- `data/` — SQLite database (auto-created, not tracked)
