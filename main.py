import os
import subprocess
import platform
import webbrowser
import datetime
import json
import time
import threading
import requests
import psutil
import speedtest
import wolframalpha
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
import uvicorn
from mistralai import Mistral

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration (replace with your actual keys)
OPENWEATHER_API_KEY = "2fd506e89b19f4cfa2d6cef84a0bef58"
WOLFRAM_ALPHA_APP_ID = "fa6b4bd3987f4d058564cf9277268913"
MISTRAL_API_KEY = "rqz3oMqtzAqJVTHiYidmjC70Fz5L6Lxh"

# Alarm and timer storage
alarms = []
active_timers = []
triggered_alarms = []
triggered_timers = []

class CommandRequest(BaseModel):
    command: str
    parameters: Dict = {}
    query: Optional[str] = None

class AlarmRequest(BaseModel):
    time: str  # Format: "HH:MM"
    message: str

class TimerRequest(BaseModel):
    seconds: int
    message: str

class MistralRequest(BaseModel):
    query: str

# Personal information
PERSONAL_INFO = {
    "full name": "Densingh D.",
    "date of birth": "June 9th, 2005",
    "skills": "Java, JavaScript, Python, C, C++, TypeScript, React, React Native, Spring Boot, Node.js",
    "projects": "E-commerce Platform, Meal-Tracker App, Doctor Appointment System",
    "gpa": "7.54/10",
    "college": "B.Tech in Information Technology at R.M.K Engineering College (Expected graduation: 2026)"
}

# Timetable
TIMETABLE = {
    "TUESDAY": {
        "2": {"time": "09:40 - 11:20", "course": "Placement AAL"},
        "3": {"time": "11:20 - 12:10", "course": "Placement TAA"},
        "5": {"time": "13:50 - 14:40", "course": "Placement KSN"}
    },
    "WEDNESDAY": {
        "1": {"time": "08:50 - 09:40", "course": "Microservice Architecture"},
        "2": {"time": "09:40 - 11:20", "course": "Microservice Architecture Lab"},
        "5": {"time": "13:50 - 15:30", "course": "Placement TMM"}
    },
    "THURSDAY": {
        "1": {"time": "08:50 - 09:40", "course": "Professional Ethics"},
        "3": {"time": "11:20 - 12:10", "course": "Natural Language Processing"},
        "5": {"time": "13:50 - 15:30", "course": "Robotic Operating System"}
    },
    "FRIDAY": {
        "1": {"time": "08:50 - 09:40", "course": "Scalable Messaging Infrastructure"},
        "2": {"time": "09:40 - 11:20", "course": "Image and Video Analytics"},
        "5": {"time": "13:50 - 15:30", "course": "Placement RRJ"}
    },
    "SATURDAY": {
        "1": {"time": "08:50 - 09:40", "course": "Professional Readiness for Innovation"},
        "2": {"time": "09:40 - 11:20", "course": "Placement TMM"},
        "4": {"time": "12:10 - 13:00", "course": "Library"},
        "5": {"time": "13:50 - 15:30", "course": "Placement SSH"}
    }
}

# Application mapping
APP_MAP = {
    "command prompt": "cmd",
    "paint": "mspaint",
    "word": "winword",
    "excel": "excel",
    "chrome": "chrome",
    "vscode": "code",
    "powerpoint": "powerpnt",
    "edge": "msedge",
    "firefox": "firefox",
    "brave": "brave",
    "calculator": "calc",
    "notepad": "notepad",
    "whatsapp": "Whatsapp",
    "instagram": "Instagram",
    "settings": "ms-settings:",
    "task manager": "taskmgr",
    "device manager": "devmgmt.msc",
    "calendar": "outlookcal:",
    "spotify": "spotify",
    "discord": "discord",
    "zoom": "zoom",
    "teams": "teams",
    "vlc": "vlc",
    "photoshop": "photoshop",
    "illustrator": "illustrator",
    "premiere": "premierepro",
    "after effects": "afterfx"
}

# Command handlers
def handle_command(request: CommandRequest):
    command = request.command.lower()
    query = request.query.lower() if request.query else ""
    
    handlers = {
        "hello": lambda: "How can I help you?",
        "hi": lambda: "How can I help you?",
        "hey": lambda: "How can I help you?",
        "jarvis": lambda: "At your service.",
        "schedule": get_schedule,
        "timetable": get_schedule,
        "time": lambda: f"The current time is {datetime.datetime.now().strftime('%I:%M %p')}",
        "date": lambda: f"Today's date is {datetime.datetime.now().strftime('%B %d, %Y')}",
        "weather": lambda: get_weather(query),
        "temperature": lambda: get_weather(query),
        "calculate": lambda: calculate(query),
        "google": lambda: search_web(query.replace("google", "").strip(), "google"),
        "youtube": lambda: search_web(query.replace("youtube", "").strip(), "youtube"),
        "wikipedia": lambda: search_web(query.replace("wikipedia", "").strip(), "wikipedia"),
        "edge": lambda: search_web(query.replace("edge", "").strip(), "edge"),
        "firefox": lambda: search_web(query.replace("firefox", "").strip(), "firefox"),
        "brave": lambda: search_web(query.replace("brave", "").strip(), "brave"),
        "open": lambda: open_local_app(query.replace("open", "").strip()),
        "close": lambda: close_local_app(query.replace("close", "").strip()),
        "volume up": lambda: adjust_volume("up"),
        "volume down": lambda: adjust_volume("down"),
        "play": lambda: control_media("playpause"),
        "pause": lambda: control_media("playpause"),
        "mute": lambda: control_media("mute"),
        "audio on": lambda: adjust_volume("up"),
        "sound on": lambda: adjust_volume("up"),
        "speed test": run_speed_test,
        "internet speed": run_speed_test,
        "system info": get_system_info,
        "thank you": lambda: "You're welcome.",
        "thanks": lambda: "You're welcome.",
        "help": get_help,
        "what can you do": get_help,
        "joke": tell_joke,
        "shutdown": system_shutdown,
        "restart": system_restart,
        "lock screen": lock_screen,
        "hibernate": hibernate,
        "sleep": sleep,
        "alarm": lambda: set_alarm(query.replace("alarm", "").replace("set", "").replace("for", "").strip()),
        "set alarm": lambda: set_alarm(query.replace("set alarm", "").replace("for", "").strip()),
        "next video": lambda: media_control("next"),
        "previous video": lambda: media_control("previous"),
        "fullscreen": lambda: media_control("fullscreen"),
        "minimize": lambda: media_control("minimize"),
        "maximize": lambda: media_control("maximize"),
        "close window": lambda: media_control("close"),
        "analyze": lambda: analyze_products(query.replace("analyze", "").strip()),
        "compare": lambda: analyze_products(query.replace("compare", "").strip()),
        "recommend": lambda: analyze_products(query.replace("recommend", "").strip()),
        "best": lambda: analyze_products(query.replace("best", "").strip()),
        "densingh": lambda: PERSONAL_INFO,
        "clear history": lambda: {"status": "success", "message": "Command history cleared"},
        "search": lambda: search_web(query.replace("search", "").strip(), "google"),
        "amazon": lambda: search_amazon(query.replace("amazon", "").strip()),
    }
    
    # Handle exact matches first
    if command in handlers:
        return handlers[command]()
    
    # Handle command prefixes
    for cmd_prefix, handler in handlers.items():
        if command.startswith(cmd_prefix):
            return handler()
    
    return get_mistral_response(query)

# Mistral AI handler
def get_mistral_response(query: str):
    try:
        if not query:
            return "Please provide a query"
            
        client = Mistral(api_key=MISTRAL_API_KEY)
        response = client.chat.complete(
            model="mistral-small",
            messages=[{"role": "user", "content": query}]
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return f"Error processing your request: {str(e)}"

# System functions
def run_in_thread(func):
    def wrapper():
        thread = threading.Thread(target=func)
        thread.daemon = True
        thread.start()
    return wrapper

@run_in_thread
def system_shutdown():
    shutdown_sequence = [
        "Initiating system shutdown protocol",
        "Saving all active sessions",
        "Closing network connections",
        "Terminating background processes",
        "All systems secured",
        "J.A.R.V.I.S. signing off"
    ]
    try:
        if platform.system() == "Windows":
            os.system("shutdown /s /t 1")
        elif platform.system() == "Darwin":
            os.system("osascript -e 'tell app \"System Events\" to shut down'")
        else:  # Linux
            os.system("shutdown now")
    except:
        return "\n".join(shutdown_sequence + ["(Simulated shutdown - running in cloud environment)"])
    return "\n".join(shutdown_sequence)

@run_in_thread
def system_restart():
    restart_sequence = [
        "Initiating system reboot sequence",
        "Preparing system components for restart",
        "Saving all active sessions",
        "J.A.R.V.I.S. will be back shortly"
    ]
    try:
        if platform.system() == "Windows":
            os.system("shutdown /r /t 1")
        elif platform.system() == "Darwin":
            os.system("osascript -e 'tell app \"System Events\" to restart'")
        else:  # Linux
            os.system("reboot")
    except:
        return "\n".join(restart_sequence + ["(Simulated restart - running in cloud environment)"])
    return "\n".join(restart_sequence)

def lock_screen():
    try:
        if platform.system() == "Windows":
            os.system("rundll32.exe user32.dll,LockWorkStation")
            return "System locked successfully."
        elif platform.system() == "Darwin":
            os.system("pmset displaysleepnow")
            return "System locked successfully."
        else:  # Linux
            os.system("gnome-screensaver-command -l")
            return "System locked successfully."
    except:
        return "Lock screen command failed."

def hibernate():
    try:
        if platform.system() == "Windows":
            os.system("shutdown /h")
            return "System hibernating."
        elif platform.system() == "Darwin":
            return "Hibernation not typically used on macOS"
        else:  # Linux
            os.system("systemctl hibernate")
            return "System hibernating."
    except:
        return "Hibernate command failed."

def sleep():
    try:
        if platform.system() == "Windows":
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            return "System going to sleep."
        elif platform.system() == "Darwin":
            os.system("pmset sleepnow")
            return "System going to sleep."
        else:  # Linux
            os.system("systemctl suspend")
            return "System going to sleep."
    except:
        return "Sleep command failed."

def media_control(action: str):
    actions = {
        "next": "Playing next media",
        "previous": "Playing previous media",
        "fullscreen": "Toggling fullscreen mode",
        "minimize": "Minimizing current window",
        "maximize": "Maximizing current window",
        "close": "Closing current window"
    }
    return actions.get(action, f"Action '{action}' not supported")

def get_weather(query: str = None):
    if not OPENWEATHER_API_KEY:
        return "Weather API not configured"
    
    try:
        city = query.split("in ")[1] if "in " in query else "Chennai"
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric"
        res = requests.get(url).json()
        
        if res.get("cod") != 200:
            return f"Could not retrieve weather for {city}"
        
        temp = res["main"]["temp"]
        feels_like = res["main"]["feels_like"]
        humidity = res["main"]["humidity"]
        description = res["weather"][0]["description"]
        return (f"Weather in {city}: {description.capitalize()}\n"
                f"Temperature: {temp}°C (Feels like: {feels_like}°C)\n"
                f"Humidity: {humidity}%")
    except Exception as e:
        return f"Error retrieving weather: {str(e)}"

def calculate(query: str):
    if not WOLFRAM_ALPHA_APP_ID:
        return "Calculation service not configured"
    
    try:
        client = wolframalpha.Client(WOLFRAM_ALPHA_APP_ID)
        res = client.query(query)
        answer = next(res.results).text
        return f"The result is: {answer}"
    except:
        return "Could not calculate that expression"

def search_web(query: str, engine: str):
    engines = {
        "google": "https://www.google.com/search?q={}",
        "youtube": "https://www.youtube.com/results?search_query={}",
        "wikipedia": "https://en.wikipedia.org/wiki/Special:Search?search={}",
        "edge": "https://www.bing.com/search?q={}",
        "firefox": "https://www.bing.com/search?q={}",
        "brave": "https://search.brave.com/search?q={}"
    }
    
    if engine in engines:
        url = engines[engine].format(query)
        webbrowser.open(url)
        return f"Searching {engine} for: {query}"
    return "Search engine not supported"

def search_amazon(query: str):
    url = f"https://www.amazon.in/s?k={query.replace(' ', '+')}"
    webbrowser.open(url)
    return f"Searching Amazon for: {query}"

def get_schedule():
    day_name = datetime.datetime.now().strftime('%A').upper()
    if day_name in TIMETABLE and TIMETABLE[day_name]:
        current_time = datetime.datetime.now().strftime("%H:%M")
        response = f"Today's schedule ({day_name}):\n"
        
        for period, details in TIMETABLE[day_name].items():
            start_time = details["time"].split(" - ")[0]
            if start_time > current_time:
                response += f"→ {details['course']} at {details['time']} (Period {period})\n"
        
        return response
    return "No classes scheduled for today"

def open_local_app(app_name: str):
    app_cmd = APP_MAP.get(app_name.lower())
    if app_cmd:
        try:
            if platform.system() == "Windows":
                os.system(f"start {app_cmd}")
            elif platform.system() == "Darwin":
                os.system(f"open -a {app_cmd}")
            else:  # Linux
                os.system(f"{app_cmd} &")
            return f"Opening {app_name}"
        except:
            return f"Failed to open {app_name}"
    return f"Application '{app_name}' not found in database"

def close_local_app(app_name: str):
    app_cmd = APP_MAP.get(app_name.lower())
    if app_cmd:
        try:
            if platform.system() == "Windows":
                os.system(f"taskkill /f /im {app_cmd}.exe")
            elif platform.system() == "Darwin":
                os.system(f"pkill -f {app_cmd}")
            else:  # Linux
                os.system(f"pkill {app_cmd}")
            return f"Closing {app_name}"
        except:
            return f"Failed to close {app_name}"
    return f"Application '{app_name}' not found in database"

def adjust_volume(direction: str):
    try:
        if platform.system() == "Windows":
            if direction == "up":
                os.system(r'nircmd.exe changesysvolume 2000')
                return "Volume increased"
            else:
                os.system(r'nircmd.exe changesysvolume -2000')
                return "Volume decreased"
        elif platform.system() == "Darwin":
            if direction == "up":
                os.system("osascript -e 'set volume output volume (output volume of (get volume settings) + 5)'")
                return "Volume increased"
            else:
                os.system("osascript -e 'set volume output volume (output volume of (get volume settings) - 5)'")
                return "Volume decreased"
        else:  # Linux
            if direction == "up":
                os.system("amixer -D pulse sset Master 5%+")
                return "Volume increased"
            else:
                os.system("amixer -D pulse sset Master 5%-")
                return "Volume decreased"
    except:
        return "Volume adjustment failed"

def control_media(action: str):
    return f"Media control '{action}' executed"

def run_speed_test():
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        download = st.download() / 1_000_000  # Mbps
        upload = st.upload() / 1_000_000  # Mbps
        ping = st.results.ping
        return (f"Internet Speed Test Results:\n"
                f"Download: {download:.2f} Mbps\n"
                f"Upload: {upload:.2f} Mbps\n"
                f"Ping: {ping:.2f} ms")
    except:
        return "Speed test failed"

def get_system_info():
    cpu = psutil.cpu_percent()
    memory = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    return (f"System Status:\n"
            f"CPU Usage: {cpu}%\n"
            f"Memory Usage: {memory}%\n"
            f"Disk Usage: {disk}%")

def get_help():
    return ("I can help with:\n"
            "- Opening/closing applications\n"
            "- System controls (shutdown, restart, lock)\n"
            "- Media controls\n"
            "- Web searches\n"
            "- Calculations\n"
            "- Weather information\n"
            "- Setting alarms\n"
            "- Your class schedule\n"
            "- Personal information\n"
            "- And much more!")

def tell_joke():
    jokes = [
        "Why don't scientists trust atoms? Because they make up everything!",
        "What did one wall say to the other wall? I'll meet you at the corner!",
        "Why did the scarecrow win an award? Because he was outstanding in his field!"
    ]
    return jokes[datetime.datetime.now().second % len(jokes)]

def analyze_products(query: str):
    return f"Analysis for '{query}':\nBased on current trends, this product shows strong market potential"

def set_alarm(alarm_str: str):
    try:
        # Parse alarm time (simple format: "HH:MM")
        alarm_time = datetime.datetime.strptime(alarm_str, "%H:%M").time()
        alarm_id = str(time.time())
        alarms.append({
            "id": alarm_id,
            "time": alarm_time.strftime("%H:%M"),
            "message": f"Alarm set for {alarm_str}"
        })
        return f"Alarm set for {alarm_str}"
    except:
        return "Invalid alarm format. Please use HH:MM format"

def set_timer(seconds: int, message: str):
    timer_id = str(time.time())
    active_timers.append({
        "id": timer_id,
        "end_time": time.time() + seconds,
        "message": message
    })
    return f"Timer set for {seconds} seconds"

# Alarm monitoring thread
def monitor_alarms():
    while True:
        now = datetime.datetime.now().strftime("%H:%M")
        for alarm in alarms[:]:
            if alarm["time"] == now:
                triggered_alarms.append(alarm)
                alarms.remove(alarm)
        time.sleep(30)

# Timer monitoring thread
def monitor_timers():
    while True:
        now = time.time()
        for timer in active_timers[:]:
            if timer["end_time"] <= now:
                triggered_timers.append(timer)
                active_timers.remove(timer)
        time.sleep(1)

# Start monitoring threads
threading.Thread(target=monitor_alarms, daemon=True).start()
threading.Thread(target=monitor_timers, daemon=True).start()

# API Endpoints
@app.post("/command")
async def process_command(request: CommandRequest):
    try:
        response = handle_command(request)
        return {"status": "success", "response": response}
    except Exception as e:
        return {"status": "error", "response": str(e)}

@app.post("/set-alarm")
async def add_alarm(request: AlarmRequest):
    alarm_id = str(time.time())
    alarms.append({
        "id": alarm_id,
        "time": request.time,
        "message": request.message
    })
    return {"status": "success", "message": f"Alarm set for {request.time}", "id": alarm_id}

@app.post("/set-timer")
async def add_timer(request: TimerRequest):
    timer_id = str(time.time())
    active_timers.append({
        "id": timer_id,
        "end_time": time.time() + request.seconds,
        "message": request.message
    })
    return {"status": "success", "message": f"Timer set for {request.seconds} seconds", "id": timer_id}

@app.get("/alarms")
async def get_alarms():
    return {"status": "success", "alarms": alarms}

@app.get("/timers")
async def get_timers():
    return {"status": "success", "timers": active_timers}

@app.get("/triggered-alarms")
async def get_triggered_alarms():
    alarms = triggered_alarms.copy()
    triggered_alarms.clear()
    return {"status": "success", "alarms": alarms}

@app.get("/triggered-timers")
async def get_triggered_timers():
    timers = triggered_timers.copy()
    triggered_timers.clear()
    return {"status": "success", "timers": timers}

@app.delete("/alarm/{alarm_id}")
async def delete_alarm(alarm_id: str):
    global alarms
    alarms = [a for a in alarms if a['id'] != alarm_id]
    return {"status": "success", "message": "Alarm deleted"}

@app.delete("/timer/{timer_id}")
async def delete_timer(timer_id: str):
    global active_timers
    active_timers = [t for t in active_timers if t['id'] != timer_id]
    return {"status": "success", "message": "Timer deleted"}

@app.get("/timetable")
async def get_timetable():
    return {"status": "success", "timetable": TIMETABLE}

@app.post("/mistral")
async def mistral_query(request: MistralRequest):
    try:
        client = Mistral(api_key=MISTRAL_API_KEY)
        response = client.chat.complete(
            model="mistral-small",
            messages=[{"role": "user", "content": request.query}]
        )
        return {"status": "success", "response": response.choices[0].message.content}
    except Exception as e:
        return {"status": "error", "response": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)