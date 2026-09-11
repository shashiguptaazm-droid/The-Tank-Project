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

def upload(ftp, remote, local, backup=False):
    if backup:
        try:
            ftp.rename(remote, remote + ".bak-cashfree")
            print(f"Backed up {remote}")
        except Exception as e:
            print(f"Backup failed for {remote}: {e}")

    with open(local, "rb") as f:
        ftp.storbinary("STOR " + remote, f)
    print(f"Uploaded {remote}")

try:
    ftp = CustomFTP()
    ftp.connect(HOST, 21, timeout=30)
    ftp.login(USER, PASS)
    ftp.set_pasv(True)

    # 1. Update api_key.php
    upload(ftp, "/api_key.php", "backend/api_key.php", backup=True)

    # 2. Upload new API files
    # Ensure /api directory exists (it should, but just in case)
    try:
        ftp.cwd("/api")
    except:
        ftp.mkd("/api")
        ftp.cwd("/api")

    upload(ftp, "/api/create_order.php", "backend/api/create_order.php")
    upload(ftp, "/api/cashfree_webhook.php", "backend/api/cashfree_webhook.php")
    upload(ftp, "/api/payment_return.php", "backend/api/payment_return.php")

    ftp.quit()
    print("Deployment successful!")

except Exception as e:
    print(f"Deployment failed: {e}")
