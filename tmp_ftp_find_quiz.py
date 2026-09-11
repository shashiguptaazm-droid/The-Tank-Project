from ftplib import FTP, parse229, parse227
import os, sys

HOST = "ftp.medigyaan.xyz"
USER = "Owner@medigyaan.xyz"
PASS = "MeriMaa007"

class CustomFTP(FTP):
    def makepasv(self):
        try:
            resp = self.sendcmd("EPSV")
            host, port = parse229(resp, self.sock.getpeername())
            return host, port
        except Exception:
            resp = self.sendcmd("PASV")
            if resp.startswith("229"):
                host, port = parse229(resp, self.sock.getpeername())
            else:
                host, port = parse227(resp)
            return host, port

ftp = CustomFTP()
ftp.connect(HOST, 21, timeout=30)
ftp.login(USER, PASS)
ftp.set_pasv(True)

def ls(path):
    out = []
    try:
        ftp.retrlines("MLSD " + path, out.append)
        return out
    except Exception:
        out2 = []
        try:
            ftp.retrlines("LIST " + path, out2.append)
        except Exception:
            return []
        # parse LIST line: type marker 'd' at col 0
        items = []
        for ln in out2:
            if len(ln) > 40:
                name = ln[40:].strip()
                items.append(("dir" if ln.startswith("d") else "file", name))
        return items

def parse_mlsd(entries):
    items = []
    for e in entries:
        parts = e.split(";")
        if len(parts) < 2:
            continue
        facts = {}
        name = ""
        for p in parts[:-1]:
            if "=" in p:
                k, v = p.split("=", 1)
                facts[k] = v
        name = parts[-1].strip()
        if not name or name in (".", ".."):
            continue
        typ = facts.get("type", "file")
        items.append((typ, name, facts.get("size", "?")))
    return items

matches = []
root_items = []
try:
    root_items = parse_mlsd(ls("/"))
except Exception as e:
    print("root MLSD failed:", e)

print("=== ROOT ===")
for typ, name, size in root_items:
    print("  [%s] %s" % (typ, name))

# walk recursively (depth <= 4), collecting quiz-named files
def walk(path, depth):
    if depth > 4:
        return
    try:
        items = parse_mlsd(ls(path))
    except Exception:
        return
    for typ, name, size in items:
        full = (path.rstrip("/") + "/" + name)
        if typ == "dir":
            if depth < 4:
                walk(full, depth + 1)
        else:
            low = name.lower()
            if "quiz" in low:
                matches.append((full, size, typ))

walk("/", 1)
print()
print("=== FILES WITH 'quiz' IN NAME (%d) ===" % len(matches))
for full, size, typ in matches:
    print("  %s  (%s bytes)" % (full, size))

ftp.quit()