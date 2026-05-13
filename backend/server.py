from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
import asyncio
import json
import time
import pyautogui
import webview
import threading
import queue
import speech_recognition as sr
from .brain import get_jinu_response
from .memory import init_db
from .watcher import sse_queue

app = FastAPI()

# TTS Setup
is_muted = False
tts_queue = queue.Queue()

import subprocess
import re

def clean_text_for_speech(text):
    text = re.sub(r'```.*?```', ' code block ', text, flags=re.DOTALL)
    text = re.sub(r'`.*?`', '', text)
    text = text.replace('*', '').replace('_', '').replace('#', '')
    return text.strip()

def tts_worker():
    while True:
        raw_text = tts_queue.get()
        if raw_text is None: break
        if not is_muted:
            try:
                text = clean_text_for_speech(raw_text)
                # Escape single quotes for PowerShell
                safe_text = str(text).replace("'", "''")
                ps_script = f"""
                Add-Type -AssemblyName System.Speech
                $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
                $synth.Rate = 2
                try {{ $synth.SelectVoice('Microsoft David Desktop') }} catch {{ }}
                $synth.Speak('{safe_text}')
                """
                subprocess.run(["powershell", "-Command", ps_script], creationflags=subprocess.CREATE_NO_WINDOW)
            except Exception as e:
                print(f"TTS Error: {e}")

# Start TTS background thread
threading.Thread(target=tts_worker, daemon=True).start()

def speak(text):
    if not is_muted:
        tts_queue.put(text)

# Allow CORS for frontend communication if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    message: str

@app.on_event("startup")
def startup_event():
    init_db()

@app.post("/chat")
def chat_endpoint(msg: ChatMessage):
    keywords = ["look at this", "this drawing", "on my screen", "see this", "what is this", "this picture", "this image", "can you see", "check this out", "my screen"]
    msg_lower = msg.message.lower()
    
    requires_vision = any(kw in msg_lower for kw in keywords)
    img = None
    
    if requires_vision:
        try:
            # Try to hide JINU window so it doesn't block the screen
            if len(webview.windows) > 0:
                webview.windows[0].hide()
            time.sleep(0.2) # Wait for window to disappear
            
            # Take screenshot
            img = pyautogui.screenshot()
            
            # Show JINU window again
            if len(webview.windows) > 0:
                webview.windows[0].show()
        except Exception as e:
            print(f"Error capturing screen: {e}")
            
    reply = get_jinu_response(msg.message, image=img)
    speak(reply)
    return {"reply": reply}

@app.post("/toggle_mute")
def toggle_mute():
    global is_muted
    is_muted = not is_muted
    return {"muted": is_muted}

@app.post("/listen")
def listen_endpoint():
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            text = recognizer.recognize_google(audio)
            return {"text": text}
    except sr.WaitTimeoutError:
        return {"error": "Listening timed out."}
    except sr.UnknownValueError:
        return {"error": "Could not understand audio."}
    except Exception as e:
        return {"error": f"Microphone error: {str(e)}"}

@app.get("/stream")
async def message_stream(request: Request):
    async def event_generator():
        while True:
            # If client closes connection, stop sending events
            if await request.is_disconnected():
                break
                
            # Check if there is a message in the queue
            if not sse_queue.empty():
                msg = sse_queue.get()
                yield json.dumps({"reply": msg})
            
            await asyncio.sleep(0.5)
            
    return EventSourceResponse(event_generator())

def run_server():
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
