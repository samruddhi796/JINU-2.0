import time
import threading
import pygetwindow as gw
import pyautogui
import psutil
from plyer import notification
from .brain import generate_proactive_message
from .memory import log_activity
import queue

# Global queue for SSE events to be picked up by the FastAPI server
sse_queue = queue.Queue()

def push_notification(message):
    # 1. Desktop notification using plyer
    notification.notify(
        title="JINU",
        message=message,
        app_name="JINU 2.0",
        timeout=5
    )
    # 2. Push to SSE queue for in-app chat
    sse_queue.put(message)

def watcher_loop():
    print("Watcher Agent started...")
    
    last_mouse_pos = pyautogui.position()
    idle_time = 0
    youtube_time = 0
    vscode_opened = False
    
    while True:
        try:
            # Check Active Window
            active_window = gw.getActiveWindow()
            if active_window:
                window_title = active_window.title
                # Extract simple app name from window title (usually 'Title - App Name')
                app_name = window_title.split(" - ")[-1] if " - " in window_title else "Unknown App"
                log_activity(app_name, window_title, 5)
                
                # Triggers
                if "YouTube" in window_title or "Netflix" in window_title:
                    youtube_time += 5
                    if youtube_time == 1200: # 20 minutes
                        msg = generate_proactive_message("distraction_long", f"User has been on {window_title} for 20 minutes.")
                        push_notification(msg)
                else:
                    youtube_time = 0 # reset
                
                if ("Code" in window_title or "VSCode" in window_title) and not vscode_opened:
                    vscode_opened = True
                    msg = generate_proactive_message("coding_detected", "User just opened VS Code.")
                    push_notification(msg)

            # Check Idle Time
            current_mouse_pos = pyautogui.position()
            if current_mouse_pos == last_mouse_pos:
                idle_time += 5
                if idle_time == 600: # 10 minutes
                    msg = generate_proactive_message("user_idle", "User has been idle for 10 minutes.")
                    push_notification(msg)
            else:
                if idle_time >= 600:
                    msg = generate_proactive_message("user_returned", "User has returned after being idle.")
                    push_notification(msg)
                idle_time = 0
                last_mouse_pos = current_mouse_pos
                
        except Exception as e:
            print(f"Watcher error: {e}")
            
        time.sleep(5)

def start_watcher():
    watcher_thread = threading.Thread(target=watcher_loop, daemon=True)
    watcher_thread.start()
