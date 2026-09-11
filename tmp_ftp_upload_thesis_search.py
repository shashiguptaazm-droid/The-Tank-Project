#!/usr/bin/env python
"""Uploads thesis_topics_search.php to the MediGyaan FTP server
(root == https://medigyaan.xyz/Neurons/) and verifies it landed."""
import ftplib
import os
import re
import sys
import time

HOST = "ftp.medigyaan.xyz"
USER = "Owner@medigyaan.xyz"
PASS = "MeriMaa007"

SRC = os.path.join("medigyaan_backend", "thesis_topics_search.php")
DEST = "thesis_topics_search.php"


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
    if not os.path.isfile(SRC):
        print("Missing local file:", SRC)
        sys.exit(1)
    print("Local size:", os.path.getsize(SRC), "bytes")

    ftp = connect()
    try:
        with open(SRC, "rb") as fh:
            ftp.storbinary("STOR " + DEST, fh)
        print("UPLOADED", DEST)

        lines = []
        ftp.retrlines("LIST", lines.append)
        for line in lines:
            if DEST in line:
                print("Remote:", line)
        print("Done.")
    finally:
        ftp.quit()


if __name__ == "__main__":
    main()
