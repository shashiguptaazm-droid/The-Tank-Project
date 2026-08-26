"""Intent detection engine — converts natural language to tool actions.
Complete coding agent with 100+ natural language intents."""
import re
import os

PROJECT = "/home/shashi/The-Tank-Project"
SCRIPTS = f"{PROJECT}/scripts"
ARDUINO_SSH = "sshpass -p '9936468425' ssh -o StrictHostKeyChecking=no arduino@192.168.31.72"


def infer_action(user_msg: str, history: list = None) -> dict:
    """Infer the right action from the user's message, ignoring model output."""
    lower = user_msg.lower().strip()
    original = user_msg.strip()

    # ══════════════════════════════════════════════════════════════
    #  CODING AGENT — file operations, code generation, debugging
    # ══════════════════════════════════════════════════════════════

    # ── READ / SHOW FILE ──
    if any(w in lower for w in ["read file", "show file", "cat ", "open file",
                                  "display file", "what's in", "show me",
                                  "what does", "contents of", "view file"]):
        path = _extract_path(user_msg)
        if path:
            return {"action": "shell", "cmd": f"head -100 {path}"}
        return {"action": "reply", "text": "Specify a file path: read file /path/to/file"}

    # ── WRITE / CREATE FILE ──
    if any(w in lower for w in ["write file", "create file", "make file",
                                  "new file", "save file"]):
        path = _extract_path(user_msg)
        if path:
            # Check if file exists first
            return {"action": "shell", "cmd": f"ls -la {path} 2>/dev/null && echo EXISTS || echo NEW_FILE:{path}"}
        return {"action": "reply", "text": "Specify a file path: write file /path/to/file.py"}

    # ── CODE GENERATION ──
    if any(w in lower for w in ["write a function", "write a class", "write a script",
                                  "write python", "write code", "generate code",
                                  "create a function", "create a class",
                                  "make a function", "make a script",
                                  "write a module", "write a test",
                                  "add a function", "add a class"]):
        # Extract what to generate
        desc = _extract_code_description(user_msg)
        return {"action": "shell", "cmd":
                f"cd {PROJECT} && echo '=== Code Generation Request ===' && echo '{desc[:200]}' && echo '=== Searching for similar patterns ===' && grep -rn 'def \\|class ' --include='*.py' | head -20"}

    # ── FIX BUG ──
    if any(w in lower for w in ["fix the bug", "fix bug", "debug", "find bug",
                                  "what's wrong", "broken", "error in",
                                  "traceback", "exception"]):
        path = _extract_path(user_msg)
        if path:
            return {"action": "shell", "cmd":
                    f"cd {PROJECT} && echo '=== Reading {path} ===' && head -100 {path} && echo '=== Syntax check ===' && python3 -m py_compile {path} 2>&1"}
        return {"action": "shell", "cmd":
                f"cd {PROJECT} && echo '=== Recent errors ===' && grep -rn 'TODO\\|FIXME\\|BUG\\|HACK\\|XXX' --include='*.py' | head -20"}

    # ── SEARCH CODE ──
    if any(w in lower for w in ["search for", "find ", "grep", "look for",
                                  "search code", "find function", "find class",
                                  "where is", "locate", "find definition",
                                  "find references", "who uses"]):
        pattern = _extract_search_pattern(user_msg)
        if pattern:
            return {"action": "shell", "cmd":
                    f"cd {PROJECT} && grep -rn '{pattern}' --include='*.py' 2>/dev/null | head -30"}
        return {"action": "reply", "text": "Specify what to search: search for 'function_name'"}

    # ── LIST FILES ──
    if any(w in lower for w in ["list files", "ls ", "show files", "directory",
                                  "what files", "file list", "list python",
                                  "list all"]):
        path = _extract_path(user_msg) or "."
        if "python" in lower:
            return {"action": "shell", "cmd": f"find {path} -name '*.py' -type f 2>/dev/null | head -30"}
        return {"action": "shell", "cmd": f"ls -la {path} 2>/dev/null | head -30"}

    # ── EDIT / MODIFY FILE ──
    if any(w in lower for w in ["edit file", "modify file", "change file",
                                  "update file", "fix file", "patch"]):
        path = _extract_path(user_msg)
        if path:
            return {"action": "shell", "cmd": f"head -100 {path}"}
        return {"action": "reply", "text": "Specify a file path to edit"}

    # ── DELETE FILE ──
    if any(w in lower for w in ["delete file", "remove file", "rm "]):
        path = _extract_path(user_msg)
        if path:
            return {"action": "shell", "cmd": f"rm -i {path} 2>&1"}
        return {"action": "reply", "text": "Specify a file path to delete"}

    # ── SYNTAX CHECK ──
    if any(w in lower for w in ["check syntax", "syntax check", "py_compile",
                                  "lint", "check code", "code review"]):
        path = _extract_path(user_msg)
        if path:
            return {"action": "shell", "cmd": f"python3 -m py_compile {path} 2>&1 && echo 'SYNTAX OK' || echo 'SYNTAX ERROR'"}
        return {"action": "shell", "cmd":
                f"cd {PROJECT} && python3 -m py_compile tank_os/shell/terminal/agent_chat.py 2>&1 && echo SYNTAX_OK || echo SYNTAX_ERROR"}

    # ── RUN TESTS ──
    if any(w in lower for w in ["run tests", "test", "pytest", "unittest",
                                  "run test", "execute tests"]):
        path = _extract_path(user_msg)
        if path:
            return {"action": "shell", "cmd": f"cd {PROJECT} && python3 -m pytest {path} -v 2>&1 | tail -30"}
        return {"action": "shell", "cmd":
                f"cd {PROJECT} && python3 -m pytest --tb=short 2>&1 | tail -30 || python3 -m unittest discover 2>&1 | tail -20"}

    # ── BUILD / COMPILE ──
    if any(w in lower for w in ["build", "compile", "make", "cmake"]):
        return {"action": "shell", "cmd":
                f"cd {PROJECT} && ls Makefile CMakeLists.txt 2>/dev/null && make 2>&1 | tail -20 || echo 'No build system found'"}

    # ── INSTALL PACKAGE ──
    if any(w in lower for w in ["install", "pip install", "apt install"]):
        pkg = re.search(r'install\s+(\S+)', lower)
        if pkg:
            return {"action": "shell", "cmd": f"pip3 install {pkg.group(1)} 2>&1 | tail -5"}
        return {"action": "reply", "text": "Specify a package: install numpy"}

    # ── COUNT LINES / CODE STATS ──
    if any(w in lower for w in ["count lines", "lines of code", "code stats",
                                  "how many lines", "wc ", "code count"]):
        path = _extract_path(user_msg) or f"{PROJECT}"
        return {"action": "shell", "cmd":
                f"find {path} -name '*.py' -type f -exec wc -l {{}} + 2>/dev/null | sort -rn | head -20"}

    # ── GIT OPERATIONS ──
    if "git status" in lower:
        return {"action": "shell", "cmd": f"cd {PROJECT} && git status"}
    if "git log" in lower:
        return {"action": "shell", "cmd": f"cd {PROJECT} && git log --oneline -15"}
    if "git diff" in lower:
        return {"action": "shell", "cmd": f"cd {PROJECT} && git diff | head -100"}
    if "git push" in lower:
        return {"action": "shell", "cmd": f"cd {PROJECT} && git push origin main 2>&1"}
    if "git pull" in lower:
        return {"action": "shell", "cmd": f"cd {PROJECT} && git pull 2>&1"}
    if any(w in lower for w in ["git commit", "commit"]):
        msg = re.search(r'(?:commit|message)\s+(?:that\s+|says?\s+|with\s+message\s+)?["\']?(.*?)["\']?\s*$', user_msg, re.IGNORECASE)
        commit_msg = msg.group(1).strip() if msg else "update"
        return {"action": "shell", "cmd":
                f"cd {PROJECT} && git add -A && git commit -m '{commit_msg}' 2>&1"}
    if "git branch" in lower:
        return {"action": "shell", "cmd": f"cd {PROJECT} && git branch -a"}
    if "git stash" in lower:
        return {"action": "shell", "cmd": f"cd {PROJECT} && git stash 2>&1"}

    # ── PROJECT STRUCTURE ──
    if any(w in lower for w in ["project structure", "tree", "directory tree",
                                  "project layout", "codebase structure",
                                  "show structure", "project overview"]):
        return {"action": "shell", "cmd":
                f"cd {PROJECT} && find . -name '*.py' -type f | head -50 && echo '---' && ls -la"}

    # ══════════════════════════════════════════════════════════════
    #  SYSTEM OPERATIONS
    # ══════════════════════════════════════════════════════════════

    # ── SYSTEM STATUS ──
    if any(w in lower for w in ["status", "system", "health", "uptime",
                                  "how are you", "system info"]):
        return {"action": "shell", "cmd": "uname -a && free -h && df -h && uptime && hostname"}

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
                "I can read/write/edit code, run commands, manage git, debug, test, and more."}

    # ── TEMPERATURE / GPU ──
    if any(w in lower for w in ["temperature", "temp", "thermal", "cpu temp",
                                  "gpu temp"]):
        return {"action": "shell", "cmd": "cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null | xargs -I{} echo '{}C' && nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader 2>/dev/null"}
    if any(w in lower for w in ["gpu", "nvidia", "cuda"]):
        return {"action": "shell", "cmd": "nvidia-smi 2>/dev/null || echo 'No NVIDIA GPU info'"}

    # ══════════════════════════════════════════════════════════════
    #  ROBOT OPERATIONS
    # ══════════════════════════════════════════════════════════════

    # ── CAMERA ──
    if any(w in lower for w in ["camera", "see", "capture", "photo", "photograph",
                                  "look", "vision", "yolo", "detect", "what do you see",
                                  "what's in the image", "scan"]):
        if any(w in lower for w in ["sms", "send", "message", "text", "owner"]):
            return {"action": "camera", "_next": "send_sms"}
        return {"action": "camera"}

    # ── SMS ──
    if any(w in lower for w in ["sms", "send sms", "message to", "text "]):
        phone = re.search(r'(\d{10})', user_msg)
        to_num = phone.group(1) if phone else "7860245819"
        msg = ""
        for sep in ["that ", "saying ", "message ", "msg ", "text "]:
            if sep in lower:
                msg = user_msg.split(sep, 1)[1].strip().strip('"\'')
                break
        if not msg:
            msg = "Hello from TankOS"
        cmd = (f"{ARDUINO_SSH} 'python3 /home/arduino/send_sms.py "
               f"--to {to_num} --msg \"{msg}\"'")
        return {"action": "shell", "cmd": cmd}

    # ── LIDAR ──
    if any(w in lower for w in ["lidar", "distance", "range", "obstacle"]):
        return {"action": "shell", "cmd": "curl -s http://localhost:8082/api/lidar/scan | python3 -c \"import sys,json; d=json.load(sys.stdin); pts=d.get('points',[]); print(f'{len(pts)} points')\""}

    # ── TANK MOVE ──
    if any(w in lower for w in ["move forward", "go forward", "drive"]):
        return {"action": "shell", "cmd": "curl -s -X POST http://localhost:8082/api/cmd/tank_move -H 'Content-Type: application/json' -d '{\"vx\":0.3,\"wz\":0.0,\"duration_s\":2}'"}
    if any(w in lower for w in ["move backward", "go back", "reverse"]):
        return {"action": "shell", "cmd": "curl -s -X POST http://localhost:8082/api/cmd/tank_move -H 'Content-Type: application/json' -d '{\"vx\":-0.3,\"wz\":0.0,\"duration_s\":2}'"}
    if "turn left" in lower:
        return {"action": "shell", "cmd": "curl -s -X POST http://localhost:8082/api/cmd/tank_move -H 'Content-Type: application/json' -d '{\"vx\":0.0,\"wz\":0.5,\"duration_s\":1}'"}
    if "turn right" in lower:
        return {"action": "shell", "cmd": "curl -s -X POST http://localhost:8082/api/cmd/tank_move -H 'Content-Type: application/json' -d '{\"vx\":0.0,\"wz\":-0.5,\"duration_s\":1}'"}
    if any(w in lower for w in ["stop", "halt", "e-stop", "emergency"]):
        return {"action": "shell", "cmd": "curl -s -X POST http://localhost:8082/api/cmd/estop"}

    # ── ARDUINO / MODEM ──
    if any(w in lower for w in ["arduino", "ssh to arduino"]):
        return {"action": "shell", "cmd": f"{ARDUINO_SSH} 'uptime'"}
    if any(w in lower for w in ["contacts", "phonebook"]):
        return {"action": "shell", "cmd": f"{ARDUINO_SSH} 'python3 /home/arduino/list_contacts.py'"}
    if any(w in lower for w in ["read sms", "inbox", "sms messages"]):
        return {"action": "shell", "cmd": f"{ARDUINO_SSH} 'python3 /home/arduino/read_sms.py'"}
    if any(w in lower for w in ["call ", "make call", "dial"]):
        phone = re.search(r'(\d{10})', user_msg)
        if phone:
            return {"action": "shell", "cmd": f"{ARDUINO_SSH} 'python3 /home/arduino/make_call.py --number {phone.group(1)}'"}
        return {"action": "reply", "text": "Specify a phone number: call 7860245819"}

    # ══════════════════════════════════════════════════════════════
    #  GREETINGS & DEFAULT
    # ══════════════════════════════════════════════════════════════

    # ── GREETINGS ──
    if any(w in lower for w in ["hi", "hello", "hey", "sup", "howdy",
                                  "good morning", "good evening"]):
        return {"action": "reply", "text":
                "Hello! I'm TankOS Agent. I can:\n"
                "  - Read/write/edit code files\n"
                "  - Run shell commands and tests\n"
                "  - Git operations (status, commit, push)\n"
                "  - Search codebase (grep, find)\n"
                "  - Debug and fix bugs\n"
                "  - See through camera (YOLO)\n"
                "  - Send SMS via Arduino\n"
                "  - Control the tank\n"
                "What would you like me to do?"}

    # ── HELP ──
    if any(w in lower for w in ["help", "?", "commands", "what can you do"]):
        return {"action": "reply", "text":
                "=== CODING ===\n"
                "  read file /path — show file contents\n"
                "  write file /path — create file\n"
                "  search for PATTERN — grep codebase\n"
                "  fix bug in FILE — debug code\n"
                "  check syntax FILE — py_compile\n"
                "  run tests — pytest\n"
                "  count lines — code stats\n"
                "  git status/log/diff/commit/push\n"
                "\n=== ROBOT ===\n"
                "  see camera — YOLO detection\n"
                "  send sms to NUMBER that MSG\n"
                "  move forward/turn left/stop\n"
                "  lidar scan\n"
                "\n=== SYSTEM ===\n"
                "  system status\n"
                "  run COMMAND\n"
                "  processes / docker / network\n"
                "  install PACKAGE"}

    # ── DEFAULT ──
    return {"action": "reply", "text":
            f"I received: '{user_msg[:80]}'\n"
            "Try: read file, search for X, git status, run tests, "
            "see camera, send sms, system status, help"}


# ══════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════

def _extract_path(msg: str) -> str:
    """Extract a file path from user message."""
    m = re.search(r'["\'](/[^"\']+)["\']', msg)
    if m:
        return m.group(1)
    m = re.search(r'(?:file|path|to|in|at)\s+(/\S+)', msg, re.IGNORECASE)
    if m:
        return m.group(1)
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


def _extract_code_description(msg: str) -> str:
    """Extract code generation description from user message."""
    for prefix in ["write a ", "create a ", "make a ", "add a "]:
        if prefix in msg.lower():
            idx = msg.lower().find(prefix)
            return msg[idx + len(prefix):]
    return msg
