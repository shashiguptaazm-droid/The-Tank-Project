from ftplib import FTP, parse229, parse227
import os

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

def find_file(ftp, path, target):
    print(f"Searching in {path}...")
    try:
        entries = []
        ftp.retrlines("MLSD " + path, entries.append)
        for entry in entries:
            parts = entry.split(";")
            name = parts[-1].strip()
            facts = {}
            for p in parts[:-1]:
                if "=" in p:
                    k, v = p.split("=", 1)
                    facts[k] = v

            if name == target:
                print(f"FOUND! {path}/{name}")
                return f"{path}/{name}"

            if facts.get("type") == "dir" and name not in (".", ".."):
                res = find_file(ftp, f"{path}/{name}".replace("//", "/"), target)
                if res: return res
    except Exception as e:
        print(f"Error in {path}: {e}")
    return None

ftp = CustomFTP()
ftp.connect(HOST, 21, timeout=30)
ftp.login(USER, PASS)
ftp.set_pasv(True)

target_path = find_file(ftp, "/", "ExamPDF.php")
if target_path:
    print(f"Downloading {target_path}...")
    with open("ExamPDF.php", "wb") as f:
        ftp.retrbinary("RETR " + target_path, f.write)
    print("Download complete.")
else:
    print("File not found on FTP.")

ftp.quit()
