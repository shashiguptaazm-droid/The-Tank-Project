# tank_nas — systemd units

Two units gate the daily off-site rclone backup loop (P3 carry-over):

| File | Role |
|------|------|
| `tank-nas-backup.service` | one-shot service — runs the Python backup. |
| `tank-nas-backup.timer`   | daily timer at 03:30 with 0–600 s jitter. |

## Install on the Jetson

```bash
sudo cp tank-nas-backup.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now tank-nas-backup.timer
systemctl list-timers tank-nas-backup.timer
```

## Alternatives (manual cron)

If you'd rather use cron for legacy reasons, the equivalent crontab line is:

```cron
# m h dom mon dow command
30 3 * * * /usr/bin/python3 /root/the\ tank\ project/tank_ws/src/tank_nas/scripts/auto_backup.py >> /var/log/tank/backup.log 2>&1
```

## Verify

```bash
sudo systemctl start tank-nas-backup.service
journalctl -u tank-nas-backup.service -n 50
```
