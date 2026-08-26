"""Intent detection engine — converts natural language to tool actions."""
import re


def infer_action(user_msg: str, history: list = None) -> dict:
    """Infer the right action from the user's message, ignoring model output."""
    lower = user_msg.lower().strip()

    # ── GREETINGS ──
    if any(w in lower for w in ["hi", "hello", "hey", "sup", "howdy", "greetings",
                                  "good morning", "good evening", "good night"]):
        return {"action": "reply", "text":
                "Hello! I'm TankOS Agent. I can:\n"
                "  - See through the camera (YOLO detection)\n"
                "  - Send SMS via Arduino modem\n"
                "  - Check system status\n"
                "  - Read/write/edit files\n"
                "  - Run any shell command\n"
                "  - Git operations (status, commit, push)\n"
                "  - Write/fix Python code\n"
                "What would you like me to do?"}

    # ── HELP ──
    if any(w in lower for w in ["help", "?", "commands", "what can you do"]):
        return {"action": "reply", "text":
                "Available commands:\n"
                "  see camera / what do you see — YOLO detection\n"
                "  send sms to NUMBER that MSG — via Arduino\n"
                "  system status — uname, memory, disk\n"
                "  read file PATH — show file contents\n"
                "  write file PATH — create/overwrite file\n"
                "  search for PATTERN — grep codebase\n"
                "  git status / git log / git diff\n"
                "  run COMMAND — execute any shell command\n"
                "  write a python function that... — code generation\n"
                "  fix the bug in FILE — debug code"}

    # ── CAMERA ──
    if any(w in lower for w in ["camera", "see", "capture", "photo", "photograph",
                                  "look", "vision", "yolo", "detect", "what do you see",
                                  "what's in the image", "scan"]):
        if any(w in lower for w in ["sms", "send", "message", "text", "owner"]):
            # Multi-step: camera + send
            return {"action": "camera", "_next": "send_sms"}
        return {"action": "camera"}

    # ── SMS ──
    if any(w in lower for w in ["sms", "send sms", "message to", "text "]):
        phone = re.search(r'(\d{10})', user_msg)
        to_num = phone.group(1) if phone else "7860245819"
        msg = ""
        for sep in ["that ", "saying ", "message ", "msg ", "text "]:
            if sep in lower:
                msg = user_msg.lower().split(sep, 1)[1].strip().strip('"\'')
                break
        if not msg:
            msg = "Hello from TankOS"
        cmd = (f"sshpass -p '9936468425' ssh -o StrictHostKeyChecking=no "
               f"arduino@192.168.31.72 'python3 /home/arduino/send_sms.py "
               f"--to {to_num} --msg \"{msg}\"'")
        return {"action": "shell", "cmd": cmd}

    # ── SYSTEM STATUS ──
    if any(w in lower for w in ["status", "system", "health", "uptime",
                                  "how are you", "system info"]):
        return {"action": "shell", "cmd": "uname -a && free -h && df -h && uptime && hostname"}

    # ── FILE READ ──
    if any(w in lower for w in ["read file", "show file", "cat ", "open file",
                                  "display file", "what's in"]):
        path = _extract_path(user_msg)
        if path:
            return {"action": "shell", "cmd": f"cat {path}"}
        return {"action": "reply", "text": "Specify a file path: read file /path/to/file"}

    # ── FILE WRITE / CODE GENERATION ──
    if any(w in lower for w in ["write file", "create file", "make file",
                                  "write a", "create a", "make a",
                                  "write python", "write code", "generate code",
                                  "write a function", "write a class",
                                  "write a script", "write a module"]):
        path = _extract_path(user_msg)
        if path:
            return {"action": "shell", "cmd": f"echo 'Writing to {path} — please provide the code content'"}
        # Code generation without specific file
        return {"action": "shell", "cmd": f"echo 'Code generation request: {user_msg[:100]} — use opencode action for full coding tasks'"}

    # ── FILE EDIT ──
    if any(w in lower for w in ["edit file", "modify file", "change file",
                                  "update file", "fix file"]):
        path = _extract_path(user_msg)
        if path:
            return {"action": "shell", "cmd": f"cat {path}"}
        return {"action": "reply", "text": "Specify a file path to edit"}

    # ── SEARCH / GREP ──
    if any(w in lower for w in ["search for", "find ", "grep", "look for",
                                  "search code", "find function", "find class",
                                  "where is", "locate"]):
        pattern = _extract_search_pattern(user_msg)
        if pattern:
            return {"action": "shell", "cmd": f"grep -rn '{pattern}' /home/shashi/The-Tank-Project --include='*.py' 2>/dev/null | head -30"}
        return {"action": "reply", "text": "Specify what to search: search for 'function_name'"}

    # ── GIT OPERATIONS ──
    if "git status" in lower:
        return {"action": "shell", "cmd": "cd /home/shashi/The-Tank-Project && git status"}
    if "git log" in lower:
        return {"action": "shell", "cmd": "cd /home/shashi/The-Tank-Project && git log --oneline -15"}
    if "git diff" in lower:
        return {"action": "shell", "cmd": "cd /home/shashi/The-Tank-Project && git diff | head -100"}
    if "git push" in lower:
        return {"action": "shell", "cmd": "cd /home/shashi/The-Tank-Project && git push origin main 2>&1"}
    if "git pull" in lower:
        return {"action": "shell", "cmd": "cd /home/shashi/The-Tank-Project && git pull 2>&1"}
    if any(w in lower for w in ["git commit", "commit"]):
        msg = re.search(r'(?:commit|message)\s+(?:that\s+|says?\s+|with\s+message\s+)?["\']?(.*?)["\']?\s*$', user_msg, re.IGNORECASE)
        commit_msg = msg.group(1).strip() if msg else "update"
        return {"action": "shell", "cmd": f"cd /home/shashi/The-Tank-Project && git add -A && git commit -m '{commit_msg}' 2>&1"}

    # ── RUN COMMAND ──
    if any(w in lower for w in ["run ", "execute ", "run command", "shell",
                                  "bash", "terminal", "command"]):
        cmd = _extract_command(user_msg)
        if cmd:
            return {"action": "shell", "cmd": cmd}
        return {"action": "reply", "text": "Specify a command: run ls -la"}

    # ── PROCESS / SERVICE ──
    if any(w in lower for w in ["process", "running", "what's running",
                                  "ps aux", "top"]):
        return {"action": "shell", "cmd": "ps aux --sort=-%mem | head -20"}
    if any(w in lower for w in ["service", "systemctl"]):
        return {"action": "shell", "cmd": "systemctl list-units --type=service --state=running | head -20"}

    # ── DOCKER ──
    if any(w in lower for w in ["docker", "container"]):
        return {"action": "shell", "cmd": "docker ps -a 2>/dev/null || echo 'Docker not running'"}

    # ── NETWORK ──
    if any(w in lower for w in ["network", "ip address", "hostname", "wifi"]):
        return {"action": "shell", "cmd": "ip addr show | grep 'inet ' && hostname -I"}
    if any(w in lower for w in ["ping", "connectivity"]):
        host = re.search(r'ping\s+(\S+)', lower)
        h = host.group(1) if host else "8.8.8.8"
        return {"action": "shell", "cmd": f"ping -c 3 {h}"}

    # ── DISK / MEMORY ──
    if any(w in lower for w in ["disk", "storage", "space"]):
        return {"action": "shell", "cmd": "df -h && du -sh /home/shashi/* 2>/dev/null | sort -rh | head -10"}
    if any(w in lower for w in ["memory", "ram"]):
        return {"action": "shell", "cmd": "free -h && cat /proc/meminfo | head -10"}

    # ── KILL / STOP ──
    if any(w in lower for w in ["kill ", "stop process", "kill process"]):
        pid = re.search(r'(\d+)', user_msg)
        if pid:
            return {"action": "shell", "cmd": f"kill -9 {pid.group(1)}"}
        return {"action": "reply", "text": "Specify a PID: kill 12345"}

    # ── INSTALL ──
    if any(w in lower for w in ["install", "pip install", "apt install"]):
        pkg = re.search(r'install\s+(\S+)', lower)
        if pkg:
            p = pkg.group(1)
            return {"action": "shell", "cmd": f"pip3 install {p} 2>&1 | tail -5"}
        return {"action": "reply", "text": "Specify a package: install numpy"}

    # ── PYTHON CODE EXECUTION ──
    if any(w in lower for w in ["run python", "execute python", "python code",
                                  "python3 -c", "run script"]):
        code = re.search(r'(?:run|execute|that)\s+(?:python\s+)?["\']?(.*?)["\']?\s*$', user_msg, re.IGNORECASE)
        if code:
            return {"action": "shell", "cmd": f"python3 -c '{code.group(1)}'"}
        return {"action": "reply", "text": "Specify Python code: run python print('hello')"}

    # ── DATE / TIME ──
    if any(w in lower for w in ["time", "date", "what time", "what date",
                                  "current time", "current date"]):
        return {"action": "shell", "cmd": "date '+%Y-%m-%d %H:%M:%S %Z'"}

    # ── WHOAMI ──
    if any(w in lower for w in ["who are you", "whoami", "what are you",
                                  "your name", "about you"]):
        return {"action": "reply", "text":
                "I'm TankOS Agent — an AI coding assistant running on a Jetson Orin Nano robot. "
                "I have full system access and can execute shell commands, read/write files, "
                "manage git, control the camera, send SMS via Arduino, and more."}

    # ── TEMPERATURE / SENSOR ──
    if any(w in lower for w in ["temperature", "temp", "thermal", "cpu temp",
                                  "gpu temp"]):
        return {"action": "shell", "cmd": "cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null | xargs -I{} echo '{}C' && nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader 2>/dev/null"}

    # ── GPU ──
    if any(w in lower for w in ["gpu", "nvidia", "cuda"]):
        return {"action": "shell", "cmd": "nvidia-smi 2>/dev/null || echo 'No NVIDIA GPU info'"}

    # ── LIDAR ──
    if any(w in lower for w in ["lidar", "lidar scan", "distance", "range"]):
        return {"action": "shell", "cmd": "curl -s http://localhost:8082/api/lidar/scan | python3 -c \"import sys,json; d=json.load(sys.stdin); pts=d.get('points',[]); print(f'{len(pts)} points, min={min(p.get(\"distance\",0) for p in pts) if pts else 0}mm, max={max(p.get(\"distance\",0) for p in pts) if pts else 0}mm')\""}

    # ── TANK MOVE ──
    if any(w in lower for w in ["move forward", "go forward", "drive", "move tank"]):
        return {"action": "shell", "cmd": "curl -s -X POST http://localhost:8082/api/cmd/tank_move -H 'Content-Type: application/json' -d '{\"vx\":0.3,\"wz\":0.0,\"duration_s\":2}'"}
    if any(w in lower for w in ["move backward", "go back", "reverse"]):
        return {"action": "shell", "cmd": "curl -s -X POST http://localhost:8082/api/cmd/tank_move -H 'Content-Type: application/json' -d '{\"vx\":-0.3,\"wz\":0.0,\"duration_s\":2}'"}
    if any(w in lower for w in ["turn left"]):
        return {"action": "shell", "cmd": "curl -s -X POST http://localhost:8082/api/cmd/tank_move -H 'Content-Type: application/json' -d '{\"vx\":0.0,\"wz\":0.5,\"duration_s\":1}'"}
    if any(w in lower for w in ["turn right"]):
        return {"action": "shell", "cmd": "curl -s -X POST http://localhost:8082/api/cmd/tank_move -H 'Content-Type: application/json' -d '{\"vx\":0.0,\"wz\":-0.5,\"duration_s\":1}'"}
    if any(w in lower for w in ["stop", "halt", "e-stop", "emergency stop"]):
        return {"action": "shell", "cmd": "curl -s -X POST http://localhost:8082/api/cmd/estop"}

    # ── SSH TO ARDUINO ──
    if any(w in lower for w in ["arduino", "ssh to arduino"]):
        return {"action": "shell", "cmd": "sshpass -p '9936468425' ssh -o StrictHostKeyChecking=no arduino@192.168.31.72 'uptime'"}

    # ── MODEM ──
    if any(w in lower for w in ["modem", "sim", "signal"]):
        return {"action": "shell", "cmd": "sshpass -p '9936468425' ssh -o StrictHostKeyChecking=no arduino@192.168.31.72 'python3 /home/arduino/list_contacts.py'"}

    # ── CONTACTS ──
    if any(w in lower for w in ["contacts", "phonebook", "address book"]):
        return {"action": "shell", "cmd": "sshpass -p '9936468425' ssh -o StrictHostKeyChecking=no arduino@192.168.31.72 'python3 /home/arduino/list_contacts.py'"}

    # ── READ SMS ──
    if any(w in lower for w in ["read sms", "inbox", "messages", "sms messages"]):
        return {"action": "shell", "cmd": "sshpass -p '9936468425' ssh -o StrictHostKeyChecking=no arduino@192.168.31.72 'python3 /home/arduino/read_sms.py'"}

    # ── MAKE CALL ──
    if any(w in lower for w in ["call ", "make call", "dial", "phone call"]):
        phone = re.search(r'(\d{10})', user_msg)
        if phone:
            return {"action": "shell", "cmd": f"sshpass -p '9936468425' ssh -o StrictHostKeyChecking=no arduino@192.168.31.72 'python3 /home/arduino/make_call.py --number {phone.group(1)}'"}
        return {"action": "reply", "text": "Specify a phone number: call 7860245819"}

    # ── DEFAULT: prompt for clarification ──
    return {"action": "reply", "text":
            f"I received: '{user_msg[:80]}'\n"
            "Try these commands:\n"
            "  see camera — YOLO detection\n"
            "  send sms to 7860245819 that hello\n"
            "  system status\n"
            "  read file /path/to/file\n"
            "  search for 'pattern'\n"
            "  git status\n"
            "  run ls -la\n"
            "  help — full list"}


def _extract_path(msg: str) -> str:
    """Extract a file path from user message."""
    # Try quoted path
    m = re.search(r'["\'](/[^"\']+)["\']', msg)
    if m:
        return m.group(1)
    # Try unquoted path after keywords
    m = re.search(r'(?:file|path|to|in|at)\s+(/\S+)', msg, re.IGNORECASE)
    if m:
        return m.group(1)
    # Try any path-like string
    m = re.search(r'(/\S+\.\w+)', msg)
    if m:
        return m.group(1)
    return ""


def _extract_search_pattern(msg: str) -> str:
    """Extract search pattern from user message."""
    m = re.search(r'(?:for|pattern|keyword)\s+["\']?(\S+?)["\']?\s*$', msg, re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r'search\s+(?:for\s+)?(\S+)', msg, re.IGNORECASE)
    if m:
        return m.group(1)
    return ""


def _extract_command(msg: str) -> str:
    """Extract shell command from user message."""
    m = re.search(r'(?:run|execute|command)\s+["\']?(.+?)["\']?\s*$', msg, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return ""
