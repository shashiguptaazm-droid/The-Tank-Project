#!/usr/bin/env python
"""
Uploads the follow/messenger PHP files (mirrored in backend/) to the
MediGyaan FTP server (root == https://medigyaan.xyz/Neurons/).

Usage:  python upload_follow_messenger_phps.py
"""
import ftplib
import os
import re
import sys
import time

HOST = "ftp.medigyaan.xyz"
USER = "Owner@medigyaan.xyz"
PASS = "MeriMaa007"

FILES = [
    "messenger_api.php",
    "follow_unfollow_apiv4.php",
    "followers.php",
    "following.php",
    "get_close_friends.php",
    "get_profilev1.php",
    "fetch_messenger_notifications.php",
    "follow_unfollow.php",
]


class Ftp(ftplib.FTP):
    def makepasv(self):
        resp = self.sendcmd("EPSV")
        m = re.search(r"\(\|\|\|(\d+)\|\)", resp)
        return self.sock.getpeername()[0], int(m.group(1))


def connect():
    last = None
    for i in range(5):
        try:
            ftp = Ftp(HOST, timeout=25)
            ftp.login(USER, PASS)
            return ftp
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"connect attempt {i} failed: {e}", file=sys.stderr)
            time.sleep(10)
    raise last


def main():
    missing = [f for f in FILES if not os.path.isfile(os.path.join("backend", f))]
    if missing:
        print("Missing local files:", missing)
        sys.exit(1)

    ftp = connect()
    try:
        for f in FILES:
            with open(os.path.join("backend", f), "rb") as fh:
                ftp.storbinary("STOR " + f, fh)
            print("UPLOADED", f)

        lines = []
        ftp.retrlines("LIST", lines.append)
        sizes = {}
        for line in lines:
            parts = line.split()
            if len(parts) >= 9:
                sizes[" ".join(parts[8:])] = parts[4]
        print("\nRemote verification:")
        ok = True
        for f in FILES:
            state = sizes.get(f, "MISSING?")
            print("  ", f, state)
            if state == "MISSING?":
                ok = False
        sys.exit(0 if ok else 1)
    finally:
        ftp.quit()


if __name__ == "__main__":
    main()
