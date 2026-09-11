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

ftp = CustomFTP()
ftp.connect(HOST, 21, timeout=30)
ftp.login(USER, PASS)
ftp.set_pasv(True)

out = []
try:
    ftp.cwd("/api")
    ftp.retrlines("LIST", out.append)
except Exception as e:
    print("ERR", e)
print("=== /api ===")
for it in out:
    parts = it.split(None, 8)
    if len(parts) >= 9 and parts[8] not in (".", ".."):
        print(("DIR  " if parts[0].startswith("d") else "FILE ") + parts[8])

os.makedirs("tmp_php", exist_ok=True)
for name in ["searchv2.php", "getQuestions.php", "getTopics.php", "topicsearch.php",
             "get_single_question.php", "submitAnswerx1.php", "getuserquizzes.php"]:
    try:
        with open("tmp_php/" + name, "wb") as f:
            ftp.retrbinary("RETR /api/" + name, f.write)
        print("downloaded", name)
    except Exception as e:
        print("ERR download", name, e)

ftp.quit()
