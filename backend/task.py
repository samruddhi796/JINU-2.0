import subprocess
import webbrowser
import threading
import psutil
import os
from plyer import notification
from .watcher import sse_queue
from .config import APP_WHITELIST

def open_app(name: str):
    try:
        # Check whitelist first
        is_allowed = any(allowed in name.lower() for allowed in APP_WHITELIST)
        if not is_allowed:
            return f"Opening '{name}' is blocked by the app whitelist."

        if "code" in name.lower() or "vscode" in name.lower():
            subprocess.Popen("code", shell=True)
            return "Opened VS Code."
        elif "chrome" in name.lower():
            subprocess.Popen("start chrome", shell=True)
            return "Opened Google Chrome."
        elif "notepad" in name.lower():
            subprocess.Popen("notepad", shell=True)
            return "Opened Notepad."
        elif "whatsapp" in name.lower():
            subprocess.Popen("start whatsapp:", shell=True)
            return "Opened WhatsApp."
        else:
            # Fallback
            subprocess.Popen(f"start {name}", shell=True)
            return f"Attempted to open {name}."
    except Exception as e:
        return f"Failed to open {name}: {str(e)}"

def open_folder(path: str):
    try:
        # Resolve common folders
        home = os.path.expanduser("~")
        if "document" in path.lower():
            target_path = os.path.join(home, "Documents")
        elif "download" in path.lower():
            target_path = os.path.join(home, "Downloads")
        elif "desktop" in path.lower():
            target_path = os.path.join(home, "Desktop")
        elif "picture" in path.lower():
            target_path = os.path.join(home, "Pictures")
        else:
            target_path = path

        subprocess.Popen(f'explorer "{target_path}"', shell=True)
        return f"Opened folder: {target_path}"
    except Exception as e:
        return f"Failed to open folder: {str(e)}"

def web_search(query: str):
    try:
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        webbrowser.open(url)
        return f"Searched the web for '{query}'."
    except Exception as e:
        return f"Failed to perform web search: {str(e)}"

def set_timer(minutes: int):
    try:
        def timer_done():
            import winsound
            import subprocess
            
            # Play the Windows Exclamation sound
            winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
            
            # Send Toast Notification
            notification.notify(
                title="JINU Timer",
                message=f"Your {minutes}-minute timer is done!",
                app_name="JINU 2.0",
                timeout=10
            )
            
            # Add to chat stream
            msg = f"Timer done! {minutes} minutes have passed."
            sse_queue.put(msg)
            
            # Speak out loud using PowerShell TTS
            ps_script = f"""
            Add-Type -AssemblyName System.Speech
            $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
            $synth.Rate = 2
            try {{ $synth.SelectVoice('Microsoft David Desktop') }} catch {{ }}
            $synth.Speak('Timer is up! {minutes} minutes have passed.')
            """
            subprocess.run(["powershell", "-Command", ps_script], creationflags=subprocess.CREATE_NO_WINDOW)
            
        t = threading.Timer(minutes * 60, timer_done)
        t.daemon = True
        t.start()
        return f"Timer set for {minutes} minutes."
    except Exception as e:
        return f"Failed to set timer: {str(e)}"

def take_note(note: str):
    # We could save this to SQLite or a file
    try:
        notes_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        os.makedirs(notes_dir, exist_ok=True)
        with open(os.path.join(notes_dir, "notes.txt"), "a") as f:
            f.write(f"- {note}\n")
        return "Note saved successfully."
    except Exception as e:
        return f"Failed to save note: {str(e)}"

def system_info():
    try:
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        battery = psutil.sensors_battery()
        bat_str = f"{battery.percent}%" if battery else "Desktop (No Battery)"
        return f"System Info: CPU at {cpu}%, RAM at {ram}%, Battery at {bat_str}."
    except Exception as e:
        return f"Failed to get system info: {str(e)}"

def execute_task(task_json: dict):
    action = task_json.get("action")
    target = task_json.get("target")
    
    if action == "open_app":
        return open_app(target)
    elif action == "open_folder":
        return open_folder(target)
    elif action == "web_search":
        return web_search(target)
    elif action == "set_timer":
        try:
            import re
            mins_match = re.search(r'\d+', str(target))
            if mins_match:
                mins = int(mins_match.group(0))
                return set_timer(mins)
            else:
                return "Invalid timer duration: no number found."
        except:
            return "Invalid timer duration."
    elif action == "take_note":
        return take_note(target)
    elif action == "system_info":
        return system_info()
    else:
        return f"Unknown action: {action}"
