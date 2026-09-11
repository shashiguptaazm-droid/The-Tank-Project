from ftplib import FTP, parse229, parse227

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

test_php = """<?php
echo "HELLO";
?>"""

with open("backend/api/hello.php", "w") as f:
    f.write(test_php)

ftp = CustomFTP()
ftp.connect(HOST, 21)
ftp.login(USER, PASS)
ftp.cwd("/api")
with open("backend/api/hello.php", "rb") as f:
    ftp.storbinary("STOR hello.php", f)
ftp.quit()
print("Uploaded hello.php")
