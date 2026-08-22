#!/bin/bash
# Launch auto_learn.py in background
# Usage: bash scripts/run_auto_learn.sh
# Check progress: tail -f /tmp/auto_learn_bg.log

cd "/root/the tank project"
nohup python3 scripts/auto_learn.py > /tmp/auto_learn_bg.log 2>&1 &
PID=$!
echo $PID > /tmp/auto_learn_bg.pid
echo "✅ Auto-learn launched (PID: $PID)"
echo "   Log: tail -f /tmp/auto_learn_bg.log"
echo "   Status: ps -p $PID"
echo "   Kill: kill $PID"
