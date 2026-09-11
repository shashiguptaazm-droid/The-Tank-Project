#!/usr/bin/env python3
"""Resume the Android projects upload to the VPS (tar over SSH, per-piece resumable).

Pieces still missing on /root/android-projects:
  1. PRESENTATIONHANDLER        (full project)
  2. MediGyaanEMR               (full project)
  3. EduLabsRTM intermediates    (full intermediates tree)
  4. MediGyaan intermediates     (all subdirs EXCEPT intermediary_bundle, already on VPS)

Each piece is one `tar -C <root> -cf - <rel>` piped over ssh to `tar -xf -`.
Pieces already present (verified by size) are skipped, so re-running resumes.
"""
import os
import subprocess
import sys
import time

SSH_KEY = r"C:/Users/Shash/AndroidStudioProjects/MediGyaan/sshkeys/id_ed25519_new_vps"
HOST = "root@100.71.127.19"
SRC = r"C:/Users/Shash/AndroidStudioProjects"
DEST = "/root/android-projects"
LOG = r"C:/Users/Shash/AndroidStudioProjects/MediGyaan/tmp_vps_upload.log"

def log(msg):
    line = "%s %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def remote_size(path):
    """Return size in MB of a remote path (0 if missing)."""
    r = subprocess.run(
        ["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=12",
         HOST, "du -sm %s 2>/dev/null | cut -f1" % path],
        capture_output=True, text=True, timeout=60)
    out = (r.stdout or "").strip()
    try:
        return int(out)
    except ValueError:
        return 0

def send_piece(label, rel, min_mb, expect_mb=None):
    """rel: path relative to SRC. Skip if remote already >= min_mb."""
    log("=== %s: %s (expect >=%dMB) ===" % (label, rel, min_mb))
    # tar -C SRC rel extracts to DEST/rel on the far side
    cur = remote_size(DEST + "/" + rel.replace("\\", "/"))
    log("  remote current: %dMB (need >=%dMB)" % (cur, min_mb))
    if cur >= min_mb:
        log("  SKIP (already present)")
        return True
    # tar -C SRC -cf - rel | ssh tar -xf - -C DEST
    cmd = ["tar", "-C", SRC, "-cf", "-", rel.replace("\\", "/")]
    ssh = ["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=12",
           "-o", "ServerAliveInterval=30", HOST,
           "mkdir -p %s && tar -xf - -C %s" % (DEST, DEST)]
    t0 = time.time()
    p1 = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    p2 = subprocess.Popen(ssh, stdin=p1.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p1.stdout.close()
    err = p2.communicate(timeout=3600)[1].decode("utf-8", "replace")
    rc = p2.returncode
    dt = time.time() - t0
    if rc != 0:
        log("  FAILED rc=%d (%ds): %s" % (rc, dt, err.strip()[:200]))
        return False
    after = remote_size(DEST + "/" + rel.replace("\\", "/"))
    log("  OK rc=0 in %ds, remote now %dMB" % (dt, after))
    if expect_mb and after < expect_mb * 0.95:
        log("  WARN: expected ~%dMB, got %dMB" % (expect_mb, after))
    return True

def main():
    open(LOG, "a", encoding="utf-8").write("\n===== RESUME %s =====\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
    pieces = [
        ("PRESENTATIONHANDLER", "PRESENTATIONHANDLER", 150, 170),
        ("MediGyaanEMR", "MediGyaanEMR", 180, 206),
        ("EduLabsRTM intermediates", "EduLabsRTM/app/build/intermediates", 900, 978),
    ]
    # MediGyaan intermediates: every subdir except intermediary_bundle (already on VPS)
    inter = r"C:/Users/Shash/AndroidStudioProjects/MediGyaan/app/build/intermediates"
    for name in sorted(os.listdir(inter)):
        if name == "intermediary_bundle":
            continue
        full = os.path.join(inter, name)
        if not os.path.isdir(full):
            continue
        mb = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fns in os.walk(full) for f in fns) // (1024 * 1024)
        if mb < 1:
            continue
        pieces.append(("MediGyaan intermediates/%s" % name,
                       "MediGyaan/app/build/intermediates/" + name, max(1, mb - 1), mb))

    ok = 0
    for label, rel, min_mb, exp in pieces:
        try:
            if send_piece(label, rel, min_mb, exp):
                ok += 1
        except Exception as e:
            log("  EXCEPTION: %r" % e)
        time.sleep(2)
    log("done: %d/%d pieces OK" % (ok, len(pieces)))

if __name__ == "__main__":
    main()