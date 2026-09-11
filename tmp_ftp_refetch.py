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

os.makedirs("tmp_php", exist_ok=True)
with open("tmp_php/searchv2.php", "wb") as f:
    ftp.retrbinary("RETR /api/searchv2.php", f.write)
print("downloaded live searchv2.php")

ftp.quit()
