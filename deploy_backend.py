from ftplib import FTP, parse229, parse227
import os
import sys
import socket

host = 'ftp.medigyaan.xyz'
user = 'Owner@medigyaan.xyz'
password = 'MeriMaa007'
local_dir = r'c:\Users\Shash\AndroidStudioProjects\EduLabsRTM\backend'

class CustomFTP(FTP):
    def makepasv(self):
        # Force EPSV first to handle proxy/firewall rewriting
        try:
            print("Sending EPSV...")
            resp = self.sendcmd('EPSV')
            host, port = parse229(resp, self.sock.getpeername())
            print(f"EPSV Success: host={host}, port={port}")
            return host, port
        except Exception as e:
            print(f"EPSV failed: {e}. Falling back to PASV...")
            resp = self.sendcmd('PASV')
            # Check response code
            if resp.startswith('229'):
                host, port = parse229(resp, self.sock.getpeername())
                print(f"PASV returned 229, parsed via EPSV: host={host}, port={port}")
                return host, port
            else:
                host, port = parse227(resp)
                print(f"PASV Success: host={host}, port={port}")
                return host, port

try:
    print(f"Resolving host {host} to IPv4 address...")
    ipv4_address = socket.gethostbyname(host)
    print(f"Resolved to: {ipv4_address}")
    
    print(f"Connecting to FTP server at {ipv4_address}...")
    ftp = CustomFTP()
    ftp.set_debuglevel(1)
    ftp.connect(ipv4_address, 21, timeout=30)
    ftp.login(user, password)
    print("Login successful.")
    
    ftp.set_pasv(True)
    
    print("Listing remote files...")
    ftp.retrlines('LIST')
    
    def ensure_remote_dir(path):
        if not path:
            ftp.cwd('/')
            return
        ftp.cwd('/')
        for part in path.replace('\\', '/').split('/'):
            if not part:
                continue
            try:
                ftp.mkd(part)
            except Exception:
                pass
            ftp.cwd(part)

    for root, dirs, files in os.walk(local_dir):
        dirs[:] = [d for d in dirs if d not in {'vps_worker', '__pycache__'}]
        rel_dir = os.path.relpath(root, local_dir)
        remote_dir = '' if rel_dir == '.' else rel_dir.replace('\\', '/')
        ensure_remote_dir(remote_dir)

        for filename in files:
            if filename.endswith(('.php', '.html', '.sql')):
                filepath = os.path.join(root, filename)
                remote_path = f"{remote_dir}/{filename}" if remote_dir else filename
                with open(filepath, 'rb') as f:
                    print(f"Uploading {remote_path}...")
                    ftp.storbinary(f'STOR {filename}', f)
                    print(f"Uploaded {remote_path} successfully.")
                
    ftp.quit()
    print("Backend sync complete!")
except Exception as e:
    print(f"Deployment failed: {e}", file=sys.stderr)
    sys.exit(1)
