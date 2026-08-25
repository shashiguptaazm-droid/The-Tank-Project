#!/bin/bash
# reflash_test.sh — re-flash the VoiceCam app and capture boot + PING.
set -x
export PATH=$PATH:$HOME/bin
cd ~/The-Tank-Project || exit 1
B=firmware/dfrobot_camera/VoiceCam/build

python3 -m esptool --chip esp32s3 --port /dev/ttyACM0 --baud 921600 \
  --before usb-reset --after hard-reset write-flash -z \
  0x10000 "$B/VoiceCam.ino.bin" || exit 1

sleep 4
timeout 25 python3 - <<'PY'
import serial, time
try:
    s = serial.Serial('/dev/ttyACM0', 115200, timeout=3)
except Exception as e:
    print('OPEN ERROR:', e); raise SystemExit
time.sleep(2)
print('BOOT:', repr(s.read(3000)))
def line(cmd, t=6):
    s.reset_input_buffer(); s.write(cmd.encode())
    buf=b''; dl=time.time()+t
    while time.time()<dl:
        c=s.read(1)
        if not c: continue
        if c==b'\n': return buf.decode(errors='replace')
        buf+=c
    return '(timeout)'
print('PING ->', line('PING\n'))
print('STATUS ->', line('STATUS\n'))
s.close()
PY
echo DONE
