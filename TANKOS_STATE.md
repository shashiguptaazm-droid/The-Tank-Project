# TankOS State — 2026-07-30 (Complete Snapshot)
# Resume point: next Freebuff session loads this, skips re-processing

## ⚡ QUICK START (copy-paste to resume)
```bash
cd "/root/the tank project"
export GITHUB_TOKEN=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
python3 -m tank_os.shell.main                  # start shell (lightweight, no OOM)
python3 scripts/daily_evolution.py --report    # see evolution history
python3 scripts/daily_evolution.py --changelog # see what was added each day
python3 scripts/daily_evolution.py --list      # see self-maintaining ability map
```

## 🧠 KNOWLEDGE BASE (already built — no re-processing needed)
- **298 learned script files** in `tank_ws/data/learned_scripts/`
- **43 abilities** mapped to **100 learning topics**
- **3 evolution cycles** logged in `evolution_log.jsonl`
- **15 search logs** in `tank_ws/data/search_logs/`
- Self-maintaining map: new discoveries auto-added daily

## 🧬 SELF-MAINTAINING EVOLUTION (new!)
- `abilities_live.json` — dynamically discovered abilities (persists across sessions)
- `daily_changelog.jsonl` — what was added/removed each day
- Phase 2 (discover) auto-adds to live map → used by auto_learn on next cycle
- `evolve` → full cycle | `evolve --changelog` | `evolve --list` | `evolve --report`

## 🔧 SYSTEM
- **Swap**: 4GB (/swapfile, permanent in /etc/fstab)
- **RAM**: 7.8GB total, ~6GB free
- **Disk**: 127GB free on /
- **Cron**: daily evolution at 3 AM with GitHub token
- **Shell**: lightweight by default (TANKOS_FULL=1 for heavy AI engines)
- **yt-dlp**: v2026.07.04
- **ddgs**: installed and working

## 📂 KEY FILES
```
scripts/search_everything.py     540 lines — 4-source search (torrent+YT+web+GitHub)
scripts/ai_github_learner.py     460 lines — GitHub README extractor → MemoryManager
scripts/auto_learn.py            626 lines — ability→topic mapper, loads live JSON
scripts/daily_evolution.py       573 lines — 3-phase self-evolution cycle
scripts/discover.py              124 lines — search + learn in one
scripts/torrent_search.py        393 lines — torrent search with aria2 download
tank_os/shell/main.py           1411 lines — TankOS shell (lightweight default)
TANKOS_STATE.md                    this file — resume snapshot
FREEBUFF_RUNBOOK.md               pre-existing runbook
```

## 🛠 SHELL COMMANDS
```
search for X     → 4-source search + download prompt
discover X       → search + learn in one step
learn X          → GitHub README extraction → AI memory
learn --auto     → auto-learn all 43 abilities
evolve           → full self-evolution (learn + discover + expand)
evolve --changelog → show daily changelog of map changes
evolve --list    → show current ability map (built-in + discovered)
evolve --report  → show evolution history
torrent X        → torrent-only with aria2 download picker
terminal         → AI terminal REPL
```

## 🗺 NL ROUTING
```
"search for X"           → do_search
"find me X"              → do_search
"discover X"             → do_discover
"torrent X"              → do_torrent
"learn about X"          → do_learn
"evolve" / "evolve --X"  → do_evolve
```

## 📊 DATA DIRECTORY
```
tank_ws/data/
  search_logs/         15 JSON logs
  learned_scripts/    298 JSON knowledge files
  evolution/
    evolution_log.jsonl         3 cycles logged
    discovered_abilities.json    latest discovery results
    evolution_20260730.json     today's detailed report
    abilities_live.json         self-maintaining map (created on first discovery)
    daily_changelog.jsonl       what changed each day
```

## ⚙️ ENV
```bash
GITHUB_TOKEN=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
# saved in /root/.bashrc and cron
```

## ✅ ALL ISSUES RESOLVED
- OOM killer → 4GB swap + lightweight shell (TANKOS_FULL=1 for heavy engines)
- DuckDuckGo → ddgs library works
- Torrent JSON parsing → fixed
- GitHub rate limit → token: 5000 req/hr
- Qt GUI crash → disabled by default (headless VPS)
- ai_github_learner `import os` → fixed
- Shell killed → lightweight by default (<1GB RSS)

## 🔁 WHAT RUNS DAILY (cron)
```
0 3 * * *  export GITHUB_TOKEN=xxx && cd "/root/the tank project" &&
           python3 scripts/daily_evolution.py >> /tmp/evolution_cron.log 2>&1
```
- Refreshes 43 abilities from GitHub
- Searches 8 trending topics for new tool categories
- Auto-adds discoveries to live map
- Writes daily changelog
- Deep-learns new finds
