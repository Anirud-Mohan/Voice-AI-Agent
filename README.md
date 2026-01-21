# Voice Agent - Auto Service Center

A voice-based agentic application that automates customer interactions for an auto service center call center using AI-powered conversation and vehicle information management.

## Overview

This application uses LiveKit's real-time voice agents powered by Google's Gemini model to handle customer calls. The agent can:
- Welcome customers and collect vehicle information
- Look up vehicles by VIN
- Create new vehicle records
- Answer customer inquiries and direct them to appropriate departments

## Features

- **Voice I/O**: Real-time voice conversation using LiveKit
- **AI Agent**: Google Gemini 2.5 Flash with voice capabilities
- **Vehicle Management**: SQLite database for storing vehicle information
- **Function Tools**: LLM-integrated tools for database operations

## Prerequisites

- Python 3.10+
- LiveKit account and credentials
- Google API key for Gemini

## Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables in `.env`:
   ```
   LIVEKIT_URL=your_livekit_url
   LIVEKIT_API_KEY=your_api_key
   LIVEKIT_API_SECRET=your_api_secret
   GOOGLE_API_KEY=your_google_api_key
   ```

## Running the Application

```bash
python agent.py
```

## Project Structure

- `agent.py` - Main application entry point and agent orchestration
- `api.py` - LLM function tools and assistant functions
- `db_driver.py` - SQLite database driver for vehicle management
- `prompts.py` - System instructions and conversation prompts
- `requirements.txt` - Python dependencies

## Database

The application uses SQLite to store vehicle information. The database file (`auto_db.sqlite`) is automatically created on first run.

