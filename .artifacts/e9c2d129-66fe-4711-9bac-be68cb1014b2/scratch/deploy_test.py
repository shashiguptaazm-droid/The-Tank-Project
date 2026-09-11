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
echo "PHP is working. ";
$keys = require_once __DIR__ . '/../api_key.php';
if (is_array($keys)) {
    echo "api_key.php loaded successfully. APP_ID: " . $keys['CASHFREE_APP_ID'];
} else {
    echo "api_key.php failed to return array. Result: " . var_export($keys, true);
}
?>"""

with open("backend/api/test_keys.php", "w") as f:
    f.write(test_php)

ftp = CustomFTP()
ftp.connect(HOST, 21)
ftp.login(USER, PASS)
ftp.cwd("/api")
with open("backend/api/test_keys.php", "rb") as f:
    ftp.storbinary("STOR test_keys.php", f)
ftp.quit()
print("Uploaded test_keys.php")
