# Voice AI Agent - Auto Service Center

A voice-based AI application that automates customer interactions for an auto service center using real-time conversation and vehicle information management.

## 🚧 Development Status

**This project is currently in trial phase development. Many more updates and features are incoming.**

## Overview

This application uses LiveKit's real-time voice agents powered by Google's Gemini model to handle customer calls. The AI agent can:

- Welcome customers and collect vehicle information
- Look up vehicles by VIN
- Create new vehicle records
- Answer inquiries and direct customers to appropriate departments

## Tech Stack

- **Backend**: Python, Flask, LiveKit Agents SDK
- **Frontend**: React, Vite
- **AI Model**: Google Gemini 2.5 Flash
- **Database**: SQLite
- **Real-time Communication**: LiveKit

## Project Structure

```
Voice-AI-Agent/
├── backend/
│   ├── agent.py        # Voice agent orchestration
│   ├── server.py       # Flask server for token generation
│   ├── api.py          # LLM function tools
│   ├── db_driver.py    # SQLite database driver
│   └── prompts.py      # System instructions
├── frontend/
│   ├── src/            # React application
│   └── vite.config.js  # Vite configuration
└── .env                # Environment variables
```

## Prerequisites

- Python 3.10+
- Node.js 18+
- LiveKit account
- Google API key for Gemini

## Installation

1. **Clone the repository**

2. **Backend setup**:
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Frontend setup**:
   ```bash
   cd frontend
   npm install
   ```

4. **Configure environment variables** in `.env`:
   ```
   LIVEKIT_URL=your_livekit_url
   LIVEKIT_API_KEY=your_api_key
   LIVEKIT_API_SECRET=your_api_secret
   GOOGLE_API_KEY=your_google_api_key
   ```

## Running the Application

You need **three terminals** running simultaneously:

```bash
# Terminal 1 - Flask server
cd backend
python server.py

# Terminal 2 - LiveKit agent
cd backend
python agent.py dev

# Terminal 3 - Frontend
cd frontend
npm run dev
```


