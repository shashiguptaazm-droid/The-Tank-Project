#!/usr/bin/env python3
"""Probe all perception devices: LiDAR (/dev/ttyUSB0) + cameras.

Reports which protocol the LiDAR actually speaks (LD19 0x54 0x2C vs aa55)
and whether the DFRobot camera answers SNAP on /dev/ttyACM0.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def probe_lidar(port="/dev/ttyUSB0", baud=115200, seconds=2.0):
    if not Path(port).exists():
        print(f"LIDAR: FAIL — {port} not present")
        return
    try:
        import serial
    except ImportError:
        print("LIDAR: FAIL — pyserial not installed")
        return
    s = serial.Serial(port, baud, timeout=0.1)
    time.sleep(0.3)
    s.reset_input_buffer()
    buf = b""
    deadline = time.time() + seconds
    while time.time() < deadline:
        buf += s.read(4096)
    s.close()

    n = len(buf)
    ld19 = buf.count(b"\x54\x2c")   # LD14/LD19 header + verLen, 47-byte frames
    aa55 = buf.count(b"\xaa\x55")   # alternate protocol, 18-byte frames
    print(f"LIDAR: {n} bytes read from {port} @ {baud}")
    print(f"  LD19 headers (0x54 0x2C): {ld19}  -> ~{ld19 * 47 / max(n,1) * 100:.0f}% of stream")
    print(f"  aa55 headers:             {aa55}")
    print(f"  first 48 bytes: {buf[:48].hex(' ')}")
    if ld19 >= 10 and ld19 * 47 > n // 2:
        # verify frame alignment
        ok = sum(1 for i in range(0, min(len(buf), 4700), 47)
                 if buf[i:i+2] == b"\x54\x2c")
        aligned = ok == min(len(buf), 4700) // 47
        print(f"  VERDICT: LD19 47-byte frames {'ALIGNED' if aligned else 'present'}")
    elif aa55 >= 10:
        print("  VERDICT: aa55 protocol device")
    else:
        print("  VERDICT: UNKNOWN protocol or no data")


def probe_camera_serial(ports=("/dev/ttyACM0", "/dev/ttyACM1")):
    try:
        import serial
    except ImportError:
        print("CAMERA(serial): FAIL — pyserial not installed")
        return
    for port in ports:
        if not Path(port).exists():
            continue
        print(f"CAMERA(serial): probing {port} ...")
        try:
            s = serial.Serial(port, 921600, timeout=2)
            time.sleep(0.5)
            s.read(s.in_waiting)
            s.write(b"SNAP\n")
            header = b""
            deadline = time.time() + 6
            while time.time() < deadline:
                c = s.read(1)
                if c:
                    header += c
                    if c == b"\n":
                        break
            h = header.decode("utf-8", errors="replace").strip()
            print(f"  response header: {h[:80]!r}")
            if h.startswith("FRAME:"):
                parts = h.split(":")
                expected = int(parts[3])
                jpeg = b""
                dl = time.time() + 10
                while len(jpeg) < expected and time.time() < dl:
                    chunk = s.read(min(expected - len(jpeg), 16384))
                    if chunk:
                        jpeg += chunk
                jpeg += s.read(expected - len(jpeg))
                s.close()
                out = Path("/tmp/probe_cam.jpg")
                out.write_bytes(jpeg)
                valid = len(jpeg) >= 500 and jpeg[:2] == b"\xff\xd8"
                print(f"  captured {len(jpeg)} bytes, JPEG magic "
                      f"{'OK' if jpeg[:2] == b'\\xff\\xd8' else 'BAD'} -> {out}")
                print(f"  VERDICT: {'PASS' if valid else 'FAIL'}")
                return
            s.close()
        except Exception as e:
            print(f"  error: {e}")
    print("CAMERA(serial): no camera answered SNAP")


def probe_camera_http(urls):
    import urllib.request
    for url in urls:
        try:
            t0 = time.time()
            with urllib.request.urlopen(url, timeout=6) as resp:
                data = resp.read()
            ms = (time.time() - t0) * 1000
            ok = len(data) >= 500 and data[:2] == b"\xff\xd8"
            print(f"CAMERA(http): {url} -> {len(data)} bytes in {ms:.0f}ms "
                  f"[{'JPEG OK' if ok else 'not a JPEG'}]")
        except Exception as e:
            print(f"CAMERA(http): {url} -> FAIL ({e})")


if __name__ == "__main__":
    print("=" * 60)
    probe_lidar()
    print("=" * 60)
    probe_camera_serial()
    print("=" * 60)
    probe_camera_http([
        "http://192.168.31.145/snapshot.jpg",
        "http://192.168.31.145:8080/snapshot.jpg",
        "http://192.168.31.72:8083/snapshot.jpg",
        "http://192.168.31.72:8081/frame.jpg",
        "http://100.84.235.7:8083/snapshot.jpg",
    ])
