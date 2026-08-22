# TankOS Command Pipeline — Process Flow Chart

## Overview

This document shows the complete flow of a user command through the TankOS
system — from typing in the terminal to execution and output — including
every file, class, and tool involved.

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE LAYER                            │
│                                                                         │
│  ┌──────────────┐  ┌────────────────┐  ┌─────────────────────────────┐  │
│  │  SSH / TCP   │  │   Qt GUI Main  │  │  Simulation Mode CLI        │  │
│  │  (port 2223) │  │   Window       │  │  (python3 -m tank_os.shell) │  │
│  └──────┬───────┘  └──────┬─────────┘  └──────────────┬──────────────┘  │
│         │                 │                           │                  │
│         └─────────────────┴───────────────────────────┘                  │
│                                   │                                      │
│                          ┌────────▼─────────┐                           │
│                          │  TerminalREPL    │                           │
│                          │  (cli.py)        │                           │
│                          │  ┌─────────────┐ │                           │
│                          │  │ cmd.Cmd loop│ │                           │
│                          │  └──────┬──────┘ │                           │
│                          └─────────┼────────┘                           │
└────────────────────────────────────┼───────────────────────────────────┘
                                     │
                                     ▼
                  ┌──────────────────────────────────┐
                  │         SAFETY CHECK #1          │
                  │  Does input start with "!" ?     │
                  │                                  │
                  │  YES → Direct shell bypass       │
                  │  NO  → Enter NLP pipeline        │
                  └──────────────────────────────────┘
```

---

## 2. Full Command Processing Pipeline

### 2.1 User Input → TerminalEngine.interpret()

```
┌─────────────────────────────────────────────────────────────────┐
│  USER TYPES:  "find me a torrent for house of the dragon"       │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  TerminalREPL.default()  — cli.py:548                           │
│  ► Calls _execute_user_line(raw)                                │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  TerminalREPL._execute_user_line()  — cli.py:553                │
│  ► Wires ToolRegistry into engine if not already set            │
│  ► Calls self._engine.interpret(line)                           │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  TerminalEngine.interpret()  — engine.py:142                    │
│                                                                  │
│  Step 1: TerminalEngine.parse(raw)                              │
│  ► Strips whitespace                                             │
│  ► If starts with "!", removes it → direct shell bypass         │
│  ► Otherwise, returns full string for NL processing              │
│                                                                  │
│  Step 2: CommandSafety.classify(line)                            │
│  ► Checks against hard-blocked patterns (rm -rf /, etc.)        │
│  ► Returns SafetyClass: BLOCKED | DANGEROUS | MUTATING |        │
│                          READ | SAFE                             │
│                                                                  │
│  Step 3: If NOT explicit "!" command:                           │
│           Call AIRouter.natural_to_shell(line)                   │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
          ┌──────────────────────────────────────────────┐
          │           DECISION TREE BELOW                │
          │                                              │
          │  ┌─────────────────┐    ┌──────────────┐     │
          │  │  !ls -la        │    │  "list files" │     │
          │  │  → shell direct │    │  → AI router  │     │
          │  └────────┬────────┘    └───────┬──────┘     │
          │           │                     │            │
          │           ▼                     ▼            │
          │    ┌──────────────┐    ┌────────────────┐    │
          │    │  SAFETY #2   │    │  AI ROUTER     │    │
          │    │  Reclassify  │    │  (ai_router.py)│    │
          │    └──────┬───────┘    └───────┬────────┘    │
          │           │                    │             │
          └───────────┼────────────────────┼─────────────┘
                      │                    │
                      ▼                    ▼
```

### 2.2 AI Router — Natural Language to Shell

```
┌──────────────────────────────────────────────────────────────────────┐
│  AIRouter.natural_to_shell(text)  — ai_router.py:73                 │
│                                                                      │
│  1. Builds prompt: "Goal: find me a torrent...                       │
│     Return only the JSON object — no markdown fences, no prose."     │
│                                                                      │
│  2. Calls AIManager.chat(prompt, system_prompt=SYSTEM_PROMPT)        │
│     System prompt:                                                   │
│       "You translate a one-line natural-language goal into a single  │
│        POSIX shell command. Respond with strict JSON..."             │
│                                                                      │
│  3. ▸▸▸ AIManager dispatches to DEFAULT provider (rotation) ▸▸▸     │
│                                                                      │
│  4. Response parsed by _decode_reply():                              │
│     a. Try JSON.parse → extract {"command", "explanation"}           │
│     b. Fallback: look for backtick-quoted shell commands             │
│     c. Fallback: look for known shell verbs in plain text            │
│     d. If all fail → return None                                     │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │  RESULT: AIReply(command="ls *.py", explanation="...")      │     │
│  │       OR: None (if AI can't translate)                      │     │
│  └─────────────────────────────────────────────────────────────┘     │
└───────────────────────────────────┬──────────────────────────────────┘
                                    │
                                    ▼
```

### 2.3 Decision Tree — Shell vs Tools vs Unrecognized

```
                           ┌──────┐
                           │INPUT │
                           └──┬───┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
              ┌─────▼─────┐      ┌──────▼──────┐
              │ Starts     │      │ Natural     │
              │ with "!"?  │      │ Language?   │
              └─────┬─────┘      └──────┬──────┘
                    │YES                │NO → empty
                    ▼                   ▼
           ┌────────────────┐  ┌──────────────────┐
           │ Direct shell   │  │ AI NATURAL TO    │
           │ command        │  │ SHELL TRANSLATION│
           │ bypass safety  │  └────────┬─────────┘
           │ re-classify    │           │
           └───────┬────────┘     ┌─────┴──────┐
                   │              │            │
                   │         ┌────▼──┐   ┌─────▼────┐
                   │         │  AI   │   │  AI      │
                   │         │ FOUND │   │ FAILED   │
                   │         │ SHELL │   │ (None)   │
                   │         │ CMD   │   └─────┬────┘
                   │         └──┬────┘         │
                   │            │              │
                   │            ▼              ▼
                   │     ┌────────────┐  ┌──────────────┐
                   │     │ Use AI     │  │ SEARCH TOOL  │
                   │     │ command    │  │ REGISTRY     │
                   │     └──────┬─────┘  │ (engine.py:  │
                   │            │        │  _search_    │
                   │            │        │  matching_   │
                   │            │        │  tools())    │
                   │            │        └──────┬───────┘
                   │            │               │
                   │            │     ┌─────────┴────────┐
                   │            │     │                  │
                   │            │  ┌──▼──────┐    ┌──────▼───┐
                   │            │  │ Tools   │    │ No tools │
                   │            │  │ MATCHED │    │ matched  │
                   │            │  └──┬──────┘    └──────┬───┘
                   │            │     │                  │
                   │            │     ▼                  ▼
                   │            │  ┌────────────┐  ┌───────────┐
                   │            │  │ SHOW       │  │ SHOW      │
                   │            │  │ SUGGESTIONS│  │ "Sorry,   │
                   │            │  │ "invoke    │  │ couldn't  │
                   │            │  │ tool.xxx"  │  │ under-    │
                   │            │  └────────────┘  │ stand"    │
                   │            │                  └───────────┘
                   │            │
                   ▼            ▼
            ┌──────────────────────────────────┐
            │        SAFETY CLASSIFY          │
            │  Result: BLOCKED | DANGEROUS    │
            │         MUTATING | READ | SAFE  │
            └──────────────┬──────────────────┘
                           │
                           ▼
```

### 2.4 Safety Classification & Confirmation Gate

```
                    ┌─────────────────────┐
                    │  SafetyClass result │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                 │
              ▼                ▼                 ▼
     ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
     │ BLOCKED      │ │ MUTATING /   │ │ SAFE / READ  │
     │              │ │ DANGEROUS    │ │              │
     │ Print error  │ │              │ │ Execute      │
     │ "⛔ blocked" │ │ Ask user:    │ │ immediately  │
     │              │ │ "y/N" confirm│ │              │
     │ → RETURN     │ │              │ │ → run(cmd)   │
     └──────────────┘ │ ┌────────┐   │ └──────┬───────┘
                      │ │YES→run │   │        │
                      │ │NO→skip│   │        │
                      │ └────────┘   │        │
                      └──────────────┘        │
                                              │
                                              ▼
```

### 2.5 Shell Execution

```
┌──────────────────────────────────────────────────────────────────────┐
│  TerminalEngine.run(command)  — engine.py:210                       │
│                                                                      │
│  1. Safety check again (edge case)                                   │
│  2. Create SubprocessExecutor                                         │
│  3. subprocess.Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)      │
│  4. proc.communicate(timeout=30s)                                    │
│                                                                      │
│  ┌─────────────────────────────────────────────┐                     │
│  │  TIMEOUT (30s) → proc.kill() → timeout err  │                     │
│  │  SUCCESS     → stdout + stderr + exit_code  │                     │
│  │  FAILURE     → error message                │                     │
│  └─────────────────────────────────────────────┘                     │
│                                                                      │
│  5. Append to CommandHistory (for recall/explain)                    │
│  6. Emit EventBus events (for GUI/logging)                           │
│  7. Return CommandResult(command, stdout, stderr, exit_code, ...)    │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │  CommandResult dataclass:                                   │     │
│  │    command: str                                             │     │
│  │    exit_code: Optional[int]                                 │     │
│  │    stdout: str                                              │     │
│  │    stderr: str                                              │     │
│  │    duration_ms: float                                       │     │
│  │    timed_out: bool                                          │     │
│  │    safety_class: SafetyClass                                │     │
│  │    tool_suggestion_shown: bool       ← NEW FIELD            │     │
│  │    unrecognized: bool                ← NEW FIELD            │     │
│  │    error: str                                               │     │
│  └─────────────────────────────────────────────────────────────┘     │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   ▼
                   ┌──────────────────────────┐
                   │  TerminalREPL prints     │
                   │  stdout / stderr / exit  │
                   │  code to user            │
                   └──────────────────────────┘
```

---

## 3. AI Provider System (Evolution Layer)

### 3.1 Provider Registration Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│  TankShell.initialize()  — main.py                                  │
│                                                                      │
│  1. AIManager().initialize()                                         │
│     → Registers local-stub (always available)                        │
│     → Sets default from settings or "local-stub"                     │
│                                                                      │
│  2. init_evolution_providers()  — evolution_bridge.py                │
│     │                                                                │
│     ├── 2a. Register LocalLlamaProvider (GGUF offline)               │
│     │   → Scans /var/lib/tank_os/models/llm/*.gguf                  │
│     │   → Loads smallest model (if llama-cpp-python available)       │
│     │   → Name: "local-llama"                                        │
│     │                                                                 │
│     ├── 2b. Import evolution providers                               │
│     │   → GroqProvider, CerebrasProvider, MistralProvider,           │
│     │     CohereProvider, OpenRouterProvider, CloudflareProvider,    │
│     │     GeminiProvider, ReplicateProvider, DeepSeekProvider,       │
│     │     HuggingFaceProvider, EndpointAIProvider                    │
│     │                                                                 │
│     ├── 2c. Check key_registry for each provider's API key           │
│     │   → If no key → skip provider                                  │
│     │   → If key → wrap in EvolutionProviderAdapter                  │
│     │   → Register with AIManager (set_default=False)                │
│     │                                                                 │
│     └── 2d. Register RotationAdapter                                  │
│         → Wraps RotationOrchestrator                                  │
│         → Set as default (set_rotation_default=True)                  │
│         → Name: "rotation"                                            │
│                                                                      │
│  FINAL STATE: 13 providers registered                                │
│  Default: rotation (auto-fallback orchestrator)                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.2 Rotation Orchestrator Flow (Default Provider)

```
┌──────────────────────────────────────────────────────────────────────┐
│  RotationAdapter.chat(text)  — evolution_bridge.py:118              │
│                                                                      │
│  ▼                                                                   │
│  RotationOrchestrator.run(system, user)                              │
│                                                                      │
│  Tries providers in priority order (lowest number = highest pri):    │
│                                                                      │
│  ┌──────────┬─────────────┬──────────────────────────────────────┐   │
│  │ Priority │ Provider    │ Status                               │   │
│  ├──────────┼─────────────┼──────────────────────────────────────┤   │
│  │    10    │ groq        │ 🟢 llama-3.3-70b-versatile           │   │
│  │    20    │ cerebras    │ 🟢 gpt-oss-120b                      │   │
│  │    30    │ mistral     │ 🟢 mistral-large-latest              │   │
│  │    40    │ cohere      │ 🟢 command-r-plus-08-2024            │   │
│  │    50    │ openrouter  │ 🟢 openai/gpt-4o-mini                │   │
│  │    60    │ cloudflare  │ 🟢 @cf/meta/llama-3.1-8b             │   │
│  │    70    │ gemini      │ 🟢 gemini-2.5-flash                  │   │
│  │    80    │ replicate   │ 🟢 meta/meta-llama-3.3-70b           │   │
│  │    90    │ deepseek    │ 🟢 deepseek-chat                     │   │
│  │   100    │ huggingface │ 🟢 Qwen/Qwen2.5-Coder-0.5B          │   │
│  │   110    │ endpointai  │ 🟢 (configured)                      │   │
│  └──────────┴─────────────┴──────────────────────────────────────┘   │
│                                                                      │
│  For each provider:                                                   │
│    1. Check circuit breaker state                                    │
│       - OPEN (recent failures) → skip                                │
│       - HALF_OPEN (testing) → allow single request                   │
│       - CLOSED (healthy) → proceed                                   │
│    2. Call provider.prompt(system, user)                             │
│    3. If successful → return response                                │
│    4. If failed → record failure, try next provider                  │
│                                                                      │
│  If ALL providers exhausted:                                         │
│    → Return "[rotation] All providers exhausted. Try again later."   │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.3 Local LLM Provider (Offline Fallback)

```
┌──────────────────────────────────────────────────────────────────────┐
│  LocalLlamaProvider  — local_llm_provider.py                        │
│                                                                      │
│  On initialization:                                                   │
│    1. Scan /var/lib/tank_os/models/llm/*.gguf for GGUF files        │
│    2. Select smallest model for fastest startup                      │
│    3. Try to import llama-cpp-python                                 │
│    4. If available → load model into memory                          │
│    5. If not → set loaded=False, retry on first chat()               │
│                                                                      │
│  Chat flow:                                                           │
│    1. Build prompt from system + user text                           │
│    2. Call llama_cpp.Llama.create_completion()                       │
│    3. Return generated text                                          │
│                                                                      │
│  Status: 🔴 (llama-cpp-python not installed on this architecture)    │
│  When installed: 🟢 tinyllama 638MB GGUF (fastest)                   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 4. Tool System (Agent Framework)

### 4.1 Tool Discovery & Registry

```
┌──────────────────────────────────────────────────────────────────────┐
│  ToolRegistry  — agent_framework/registry.py                        │
│                                                                      │
│  Discovery:                                                          │
│    1. Scan scripts/*.py (1,166+ files)                              │
│    2. AST-parse each file for functions named cmd_*()               │
│    3. Extract docstring, F-IDs, args_schema from function defs      │
│    4. Assign category from _CATEGORIES map (51 categories)          │
│    5. Assign risk_tier from keyword analysis (high/medium/low)      │
│    6. Build ToolDefinition for each cmd_* function                   │
│                                                                      │
│  ToolDefinition fields:                                              │
│    name: str              → "diagnostics.run"                        │
│    human_name: str        → "diagnostics.run"                        │
│    description: str       → first line of docstring                  │
│    script_path: str       → "/root/.../scripts/diagnostics.py"      │
│    subcommand: str        → "run"                                    │
│    args_schema: dict      → JSON Schema for arguments                │
│    risk_tier: str         → "low" | "medium" | "high"                │
│    category: str          → "diagnostics"                            │
│    fids: list[int]        → [F151, F152, ...]                        │
│    examples: list[dict]   → CLI + curl usage examples                │
│                                                                      │
│  Commands exposed by TerminalREPL:                                   │
│    tools [--count] [--category] [--risk] [--all] [--json]           │
│    tool <name>            → show details for one tool               │
│    invoke <name> [args]   → run a tool                               │
│    search <q>             → keyword search across names + descs      │
└──────────────────────────────────────────────────────────────────────┘
```

### 4.2 Tool Invocation Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│  TerminalREPL.do_invoke(arg)  — cli.py:323                          │
│                                                                      │
│  1. Parse: "invoke diagnostics.run --dry-run"                       │
│     → tool_name = "diagnostics.run"                                  │
│     → args = {"dry_run": True}                                       │
│                                                                      │
│  2. Lookup in ToolRegistry: reg.get("diagnostics.run")               │
│     → Returns ToolDefinition or None                                 │
│                                                                      │
│  3. If risk_tier == "high":                                          │
│     → Ask user "[y/N] confirm invoke?"                              │
│                                                                      │
│  4. Create ToolCallRequest(tool_name, args, timeout_s=30)            │
│                                                                      │
│  5. Call ToolInvoker.invoke(request) — invoker.py:75                 │
│     │                                                                 │
│     ├── _build_cmd(tool, args)                                       │
│     │   → ["python3", "/root/.../scripts/diagnostics.py",            │
│     │      "run", "--dry-run"]                                       │
│     │                                                                 │
│     ├── subprocess.run(cmd, cwd=project_root, timeout=30,            │
│     │                  env=_safe_env(...))                            │
│     │   → Safe env: PATH, HOME, USER, PYTHONPATH, etc.               │
│     │   → Strips secret/API key env vars                             │
│     │                                                                 │
│     └── Returns ToolCallResponse:                                    │
│         status: "ok" | "err" | "timeout" | "unknown"                │
│         exit_code: int                                               │
│         stdout: str (truncated 8192)                                 │
│         stderr: str (truncated 4096)                                 │
│         duration_ms: int                                             │
│                                                                      │
│  6. Display result to user                                           │
│     → ✅ Status: ok (exit 0)                                         │
│     → ⏱  Duration: 1234 ms                                          │
│     → stdout: ...                                                    │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 5. Complete End-to-End Examples

### 5.1 NL → Shell Translation (Works)

```
INPUT:  "list all python files"
        │
        ▼
TerminalREPL.default() → _execute_user_line() → engine.interpret()
        │
        ▼
AIRouter.natural_to_shell("list all python files")
        │
        ▼
AIManager.chat() → RotationAdapter → Groq → "{\"command\": \"ls *.py\"}"
        │
        ▼
_decode_reply() → AIReply(command="ls *.py")
        │
        ▼
SafetyClassify("ls *.py") → SAFE
        │
        ▼
TerminalEngine.run("ls *.py")
        │
        ▼
SubprocessExecutor.execute("ls *.py") → exit 0
        │
        ▼
PRINT: ai_router.py  ai_router.py  cli.py  engine.py  safety.py  ...
       (exit 0, 5 ms)
```

### 5.2 NL → Tool Suggestion (Fallback)

```
INPUT:  "find me a torrent for house of the dragon"
        │
        ▼
AIRouter.natural_to_shell(...) → None (AI can't translate)
        │
        ▼
ai_failed = True
        │
        ▼
_search_matching_tools("find me a torrent for house of the dragon")
        │
        ▼
ToolRegistry.search("torrent download movie") → 5 matches
        │
        ▼
_format_tool_suggestions(matched_tools)
        │
        ▼
result.tool_suggestion_shown = True
        │
        ▼
PRINT: 💡 I couldn't translate that to a shell command. Try one of these tools:
         🔧 invoke download_video.pd-torrents-movie — F811 - Public Domain...
         🔧 invoke download_torrent_2.movie-trailers-pack
         🔧 invoke download_torrent_2.blender-open-movie
         📋 Or use 'tools --count' to browse all categories
```

### 5.3 Explicit Shell Command

```
INPUT:  "!echo hello world"
        │
        ▼
TerminalEngine.parse("!echo hello world") → "echo hello world"
        │
        ▼
was_explicit = True (skips AI translation)
        │
        ▼
SafetyClassify("echo hello world") → SAFE
        │
        ▼
TerminalEngine.run("echo hello world")
        │
        ▼
SubprocessExecutor.execute("echo hello world") → exit 0
        │
        ▼
PRINT: hello world
       (exit 0, 4 ms)
```

### 5.4 NL → Error Explanation

```
INPUT:  "explain"  (after a failed command)
        │
        ▼
TerminalREPL.do_explain()
        │
        ▼
engine.explain_last_error()
        │
        ▼
AIRouter.explain_error("ls /nonexistent",
    "ls: cannot access /nonexistent: No such file or directory")
        │
        ▼
AIManager.chat() → RotationAdapter → LLM
        │
        ▼
PRINT: "The ls command failed because the path /nonexistent does not
        exist. To view a directory that does exist run ls / or ls ."
```

---

## 6. File Map

```
tank_os/shell/terminal/
├── cli.py              TerminalREPL — cmd.Cmd loop, do_tools/do_invoke/do_search
├── engine.py           TerminalEngine — interpret(), run(), confirm_and_run()
├── ai_router.py        AIRouter — natural_to_shell(), explain_error()
├── safety.py           CommandSafety — classify(), blocked patterns
├── history.py          CommandHistory — append(), recall()

tank_os/core/
├── ai_manager.py       AIManager — singleton, register_provider(), chat(), dispatch
├── evolution_bridge.py EvolutionProviderAdapter, RotationAdapter, init_evolution_providers()
├── local_llm_provider.py  LocalLlamaProvider — offline GGUF inference

tank_os/agent_framework/
├── registry.py         ToolRegistry — discover(), search(), list()
├── invoker.py          ToolInvoker — invoke(), _build_cmd()
├── schemas.py          ToolDefinition, ToolCallRequest, ToolCallResponse

tank_ws/src/tank_assistant/tank_assistant/
├── evolution/
│   ├── __init__.py         build_orchestrator(), RotationOrchestrator
│   ├── providers/
│   │   ├── registry.py     register_provider(), available_providers()
│   │   ├── base.py         BaseHttpProvider (abstract)
│   │   └── concrete.py     GroqProvider, MistralProvider, CohereProvider, etc.
│   ├── orchestrators/
│   │   ├── base.py         BaseOrchestrator
│   │   └── rotation.py     RotationOrchestrator — circuit breaker fallback
│   ├── key_registry.py     KeyRegistry — API key management
│   ├── model_discovery.py  ModelDiscoverer — auto-discover models from APIs
│   └── health.py           HealthMonitor — circuit breaker state

scripts/
├── download_torrent.py     ~1,166+ CLI tools discovered by ToolRegistry
├── diagnostics.py
├── ... (51+ categories)
```

---

## 7. Data Flow Diagram

```
┌──────────┐
│  USER    │
└────┬─────┘
     │ "list python files"
     ▼
┌──────────────────┐     ┌────────────────────┐
│  TerminalREPL    │────►│ TerminalEngine     │
│  (cli.py)        │     │ (engine.py)        │
└──────────────────┘     └────────┬───────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
              ┌─────▼──────┐            ┌──────▼───────┐
              │ Command     │            │ AIRouter     │
              │ Safety      │            │ (ai_router)  │
              │ (safety.py) │            └──────┬───────┘
              └─────┬──────┘                    │
                    │                    ┌──────▼───────┐
                    │                    │ AIManager    │
                    │                    │ (ai_manager) │
                    │                    └──────┬───────┘
                    │                           │
                    │              ┌─────────────┴─────────────┐
                    │              │                           │
                    │       ┌──────▼──────┐          ┌────────▼────────┐
                    │       │ Rotation    │          │ Evolution       │
                    │       │ Adapter     │          │ Provider        │
                    │       │ (bridge)    │          │ Adapters        │
                    │       └──────┬──────┘          │ (bridge)        │
                    │              │                 └────────┬────────┘
                    │       ┌──────▼──────┐                  │
                    │       │ Rotation    │          ┌───────▼────────┐
                    │       │ Orchestrator│          │ Groq / Mistral │
                    │       │ (evolution) │          │ / Cohere / ... │
                    │       └──────┬──────┘          │ (HTTP APIs)    │
                    │              │                 └───────┬────────┘
                    │       ┌──────▼──────┐                  │
                    │       │ Circuit     │                  │
                    │       │ Breaker     │                  │
                    │       │ Check       │                  │
                    │       └─────────────┘                  │
                    │                                        │
                    ▼                                        ▼
            ┌──────────────────────────────────────────────────┐
            │            LLM RESPONSE                          │
            │  "{\"command\": \"ls *.py\", ...}"               │
            └──────────────────────┬───────────────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │  _decode_reply()             │
                    │  → AIReply(command, expl)    │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │  SafetyClassify(command)     │
                    │  → SAFE → run immediately    │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │  SubprocessExecutor          │
                    │  → shell=True                │
                    │  → capture stdout/stderr     │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │  CommandResult               │
                    │  stdout: "ai_router.py ..."  │
                    │  exit_code: 0                │
                    │  duration_ms: 5              │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │  PRINT to user               │
                    │  ai_router.py  cli.py  ...   │
                    │  (exit 0, 5 ms)              │
                    └──────────────────────────────┘
```
