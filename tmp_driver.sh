#!/bin/bash
URL="https://medigyaan.xyz/Neurons/api/zz_fix_empty_topics.php?batch=60"
H="X-App-Signature: EduLabsRTM_Secure_v1_2026"
LOG=/root/fix_topics_progress.log
echo "start $(date +%H:%M:%S)" > "$LOG"
stall=0
for i in $(seq 1 300); do
  R=$(curl -s -m 220 -H "$H" "$URL")
  echo "$i $(date +%H:%M:%S) $R" >> "$LOG"
  REM=$(echo "$R" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('remaining'))" 2>/dev/null)
  FILL=$(echo "$R" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('filled'))" 2>/dev/null)
  if [ "$REM" = "0" ]; then echo "DONE remaining=0 $(date +%H:%M:%S)" >> "$LOG"; break; fi
  if [ -z "$REM" ] || [ -z "$FILL" ]; then stall=$((stall+1)); else
    if [ "$FILL" = "0" ]; then stall=$((stall+1)); else stall=0; fi
  fi
  if [ "$stall" -ge 6 ]; then echo "STALLED after $i iterations $(date +%H:%M:%S)" >> "$LOG"; break; fi
  sleep 1
done
echo "finished $(date +%H:%M:%S)" >> "$LOG"
