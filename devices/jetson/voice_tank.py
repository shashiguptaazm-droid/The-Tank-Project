#!/usr/bin/env python3
"""Voice Tank — hands-free voice control of TankOS Agent Chat (USB-only).

Flow:
    "Hey Jarvis" (openWakeWord) → spoken reply → spoken command
    → Whisper STT → TankOS Agent Chat (camera, LiDAR, 1,166 tools, 9
    providers) → Piper TTS → the reply / options are announced through the
    DFRobot ESP32-S3 AI Camera speaker.

Hardware: the DFRobot ESP32-S3 AI Camera (DFR1154) running the VoiceCam.ino
firmware, connected to the Jetson over USB (/dev/ttyACM0). Serial protocol:
    SNAP   → JPEG frame        MIC <ms> → raw int16 PCM    SPEAK <len> → play

Usage:
    python3 devices/jetson/voice_tank.py                  # full loop
    python3 devices/jetson/voice_tank.py --test-speak hi # speaker test
    python3 devices/jetson/voice_tank.py --test-mic      # mic level test
    python3 devices/jetson/voice_tank.py --once          # one wake+command, exit

Env:
    TANK_CAM_PORT  serial port (default /dev/ttyACM0)
    PIPER_MODEL    piper voice .onnx (default: models/tts/en_US-lessac-medium.onnx)
    WHISPER_MODEL  whisper model size (default: base)
"""

from __future__ import annotations

import argparse
import contextlib
import io
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SAMPLE_RATE = 16000
MIC_POLL_MS = 1000          # window the camera sends per MIC poll
WAKE_THRESHOLD = 0.6
COMMAND_SECONDS = 4.0

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


# ─────────────────────────────────────────────────────────────────────────────
#  Camera — USB serial (VoiceCam firmware)
# ─────────────────────────────────────────────────────────────────────────────
class VoiceCam:
    """Tiny serial client for the VoiceCam.ino protocol on /dev/ttyACM0."""

    def __init__(self, port: str = "/dev/ttyACM0", baud: int = 115200):
        import serial
        self._serial = serial.Serial(port, baud, timeout=3)
        self.port = port

    def close(self) -> None:
        try:
            self._serial.close()
        except Exception:
            pass

    def open(self) -> bool:
        try:
            import serial
            if not self._serial.is_open:
                self._serial = serial.Serial(self.port, 115200, timeout=3)
            return True
        except Exception:
            return False

    def _line(self, cmd: str, timeout: float = 3.0) -> Optional[str]:
        self._serial.reset_input_buffer()
        self._serial.write(cmd.encode())
        deadline = time.monotonic() + timeout
        buf = b""
        while time.monotonic() < deadline:
            c = self._serial.read(1)
            if not c:
                continue
            if c == b"\n":
                return buf.decode(errors="replace")
            buf += c
        return None

    def ping(self) -> bool:
        return self._line("PING\n") == "PONG"

    def fetch_mic(self, ms: int = MIC_POLL_MS) -> Optional[np.ndarray]:
        """Return the camera's last `ms` of mic audio as int16 PCM (16 kHz)."""
        hdr = self._line(f"MIC {ms}\n", timeout=5.0)
        if not hdr or not hdr.startswith("AUDIO:"):
            return None
        try:
            n = int(hdr.split(":", 1)[1])
        except ValueError:
            return None
        if n <= 0:
            return np.array([], dtype=np.int16)
        data = self._serial.read(n)
        if len(data) != n:
            return None
        return np.frombuffer(data, dtype="<i2").astype(np.int16)

    def speak(self, pcm: np.ndarray) -> bool:
        """Play raw int16 PCM (16 kHz mono) through the camera speaker."""
        raw = np.asarray(pcm, dtype="<i2").tobytes()
        if not raw:
            return False
        try:
            self._serial.reset_input_buffer()
            self._serial.write(f"SPEAK {len(raw)}\n".encode())
            self._serial.write(raw)
            # wait for OK/ERR
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                line = self._serial.readline().decode(errors="replace").strip()
                if line:
                    return line == "OK"
            return False
        except Exception as e:
            print(f"[speak] error: {e}", file=sys.stderr)
            return False

    def snapshot(self, out_path: Optional[Path] = None) -> Optional[str]:
        """Grab a JPEG frame over SNAP and save it. Returns the path."""
        hdr = self._line("SNAP\n", timeout=8.0)
        if not hdr or not hdr.startswith("FRAME:"):
            return None
        parts = hdr.split(":")
        try:
            n = int(parts[3])
        except (IndexError, ValueError):
            return None
        if n <= 0:
            return None
        data = self._serial.read(n)
        if len(data) != n:
            return None
        out = out_path or (PROJECT_ROOT / "data" / "frames" / "latest.jpg")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        return str(out)


# ─────────────────────────────────────────────────────────────────────────────
#  Speech — Piper TTS
# ─────────────────────────────────────────────────────────────────────────────
def tts_wav(text: str) -> Optional[bytes]:
    model = Path(os.environ.get(
        "PIPER_MODEL", str(PROJECT_ROOT / "models" / "tts" / "en_US-lessac-medium.onnx")))
    if not model.exists():
        print(f"[tts] piper model not found: {model}", file=sys.stderr)
        return None
    try:
        proc = subprocess.run(
            ["piper", "-m", str(model), "--output_file", "-"],
            input=text.encode(), capture_output=True, timeout=60)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"[tts] piper failed: {e}", file=sys.stderr)
        return None
    if proc.returncode != 0 or not proc.stdout:
        print(f"[tts] piper error: {proc.stderr.decode(errors='replace')[:200]}", file=sys.stderr)
        return None
    return proc.stdout


def wav_to_pcm(wav: bytes) -> Optional[np.ndarray]:
    """Decode a 16 kHz / 16-bit / mono WAV into int16 PCM."""
    try:
        import struct
        if wav[:4] != b"RIFF" or wav[8:12] != b"WAVE":
            return None
        off = 12
        data_off = 0
        rate, ch, bits = 0, 1, 16
        while off + 8 <= len(wav):
            sz = struct.unpack_from("<I", wav, off + 4)[0]
            tag = wav[off:off + 4]
            if tag == b"fmt ":
                ch = struct.unpack_from("<H", wav, off + 10)[0]
                rate = struct.unpack_from("<I", wav, off + 12)[0]
                bits = struct.unpack_from("<H", wav, off + 22)[0]
            elif tag == b"data":
                data_off = off + 8
                break
            off += 8 + sz + (sz & 1)
        if not data_off or rate != SAMPLE_RATE or bits != 16 or ch == 0:
            return None
        pcm = np.frombuffer(wav[data_off:], dtype="<i2")
        if ch > 1:
            pcm = pcm.reshape(-1, ch).mean(axis=1).astype(np.int16)
        return pcm.astype(np.int16)
    except Exception:
        return None


def say(cam: VoiceCam, text: str) -> None:
    text = (text or "").strip()
    if not text:
        return
    print(f"[speak] {text}")
    wav = tts_wav(text)
    if not wav:
        return
    pcm = wav_to_pcm(wav)
    if pcm is not None and len(pcm):
        cam.speak(pcm)


# ─────────────────────────────────────────────────────────────────────────────
#  STT — Whisper
# ─────────────────────────────────────────────────────────────────────────────
_whisper = None


def transcribe(pcm: np.ndarray) -> str:
    global _whisper
    if _whisper is None:
        import whisper
        _whisper = whisper.load_model(os.environ.get("WHISPER_MODEL", "base"))
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(encode_wav(pcm))
        path = f.name
    try:
        result = _whisper.transcribe(path, fp16=False)
        return (result.get("text") or "").strip()
    finally:
        os.unlink(path)


def encode_wav(pcm: np.ndarray, rate: int = SAMPLE_RATE) -> bytes:
    import struct
    pcm = np.asarray(pcm, dtype="<i2")
    n = len(pcm)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + n * 2, b"WAVE", b"fmt ", 16, 1, 1,
        rate, rate * 2, 2, 16, b"data", n * 2)
    return header + pcm.tobytes()


# ─────────────────────────────────────────────────────────────────────────────
#  Agent — TankOS Agent Chat (tool calling)
# ─────────────────────────────────────────────────────────────────────────────
def agent_ask(text: str) -> str:
    """Send a command through TankOS Agent Chat and return the final reply.

    The camera serial port is free here — agent_chat's own SNAP capture opens
    /dev/ttyACM0 itself, so voice_tank closes its handle around the call.
    """
    sys.path.insert(0, str(PROJECT_ROOT))
    from tank_os.shell.terminal import agent_chat as ac

    import builtins
    agent = ac.AgentChat()
    buf = io.StringIO()
    orig_input = builtins.input
    builtins.input = lambda *a, **k: ""  # skip interactive face-enroll prompts
    try:
        with contextlib.redirect_stdout(buf):
            agent._handle(text)
    except Exception as e:
        print(f"[agent] error: {e}", file=sys.stderr)
    finally:
        builtins.input = orig_input
    return extract_reply(buf.getvalue())


def extract_reply(out: str) -> str:
    clean = ANSI_RE.sub("", out)
    lines = [l.strip() for l in clean.splitlines() if l.strip()]
    if not lines:
        return ""
    idx = -1
    for i, l in enumerate(lines):
        if "🤖" in l:
            idx = i
    if idx >= 0:
        return lines[idx].split("🤖", 1)[-1].strip()
    return lines[-1]


# ─────────────────────────────────────────────────────────────────────────────
#  Wake word loop
# ─────────────────────────────────────────────────────────────────────────────
class MicStream:
    """Rolls overlapping MIC polls into one continuous 16 kHz stream."""

    def __init__(self, cam: VoiceCam):
        self.cam = cam
        self.buf = np.array([], dtype=np.int16)
        self.last_t = None

    def poll(self) -> np.ndarray:
        now = time.monotonic()
        pcm = self.cam.fetch_mic(MIC_POLL_MS)
        if pcm is None or len(pcm) == 0:
            self.last_t = now
            return np.array([], dtype=np.int16)
        new = pcm
        if self.last_t is not None:
            elapsed = now - self.last_t
            n_new = int(elapsed * SAMPLE_RATE)
            if 0 < n_new < len(pcm):
                new = pcm[-n_new:]
        self.last_t = now
        self.buf = np.concatenate([self.buf, new])
        # keep ~3 s of history for the wake-word window
        max_samples = 3 * SAMPLE_RATE
        if len(self.buf) > max_samples:
            self.buf = self.buf[-max_samples:]
        return new


def wake_loop(cam: VoiceCam, once: bool = False) -> None:
    from openwakeword.model import Model
    ww = Model()
    stream = MicStream(cam)
    print("🎤 Listening for 'Hey Jarvis'… (Ctrl-C to stop)")
    while True:
        new = stream.poll()
        if len(new) == 0:
            time.sleep(0.25)
            continue
        for i in range(0, len(new), 1280):
            chunk = new[i:i + 1280]
            if len(chunk) < 640:
                continue
            pred = ww.predict(chunk.astype(np.int16))
            score = max(pred.values()) if pred else 0.0
            if score > WAKE_THRESHOLD:
                handle_wake(cam)
                stream.buf = np.array([], dtype=np.int16)
                stream.last_t = None
                if once:
                    return
                break
        time.sleep(0.2)


def record_command(cam: VoiceCam, seconds: float = COMMAND_SECONDS) -> np.ndarray:
    stream = MicStream(cam)
    deadline = time.monotonic() + seconds + 0.6
    while time.monotonic() < deadline:
        stream.poll()
        time.sleep(0.2)
    want = int(seconds * SAMPLE_RATE)
    return stream.buf[-want:] if len(stream.buf) >= want else stream.buf


def handle_wake(cam: VoiceCam) -> None:
    print("\n🔔 Wake word detected!")
    # Free the serial port briefly so nothing else blocks — then announce.
    cam.close()
    cam.open()
    say(cam, "Yes?")
    time.sleep(0.4)  # let the wake-word audio clear
    pcm = record_command(cam, seconds=COMMAND_SECONDS)
    if len(pcm) < SAMPLE_RATE:  # < 1 s
        say(cam, "I did not hear anything.")
        return
    text = transcribe(pcm)
    print(f"[stt] {text}")
    if not text.strip():
        say(cam, "Sorry, I did not catch that.")
        return
    print(f"[cmd] {text}")
    # Release the serial so agent_chat's SNAP capture can use it.
    cam.close()
    try:
        reply = agent_ask(text)
    finally:
        cam.open()
    print(f"[agent] {reply}")
    if reply:
        say(cam, reply)


# ─────────────────────────────────────────────────────────────────────────────
#  CLI
# ─────────────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(description="Voice Tank — voice control of TankOS Agent Chat (USB)")
    ap.add_argument("--port", default=os.environ.get("TANK_CAM_PORT", "/dev/ttyACM0"),
                    help="camera serial port (default: /dev/ttyACM0)")
    ap.add_argument("--test-speak", metavar="TEXT", help="speak TEXT through the camera speaker and exit")
    ap.add_argument("--test-mic", action="store_true", help="show mic levels and exit")
    ap.add_argument("--test-snap", action="store_true", help="grab one camera frame and exit")
    ap.add_argument("--once", action="store_true", help="handle a single wake+command then exit")
    args = ap.parse_args()

    cam = VoiceCam(args.port)
    ok = False
    for attempt in range(8):
        if cam.ping():
            ok = True
            break
        print(f"[cam] no response (attempt {attempt + 1}/8)…", file=sys.stderr)
        cam.close()
        time.sleep(2.5)
        cam.open()
    if not ok:
        print(f"[cam] camera not responding on {args.port} — is VoiceCam.ino flashed?",
              file=sys.stderr)
        return 1
    print(f"[cam] connected on {args.port}")

    if args.test_snap:
        path = cam.snapshot()
        print(f"[snap] {path}")
        return 0

    if args.test_speak:
        say(cam, args.test_speak)
        return 0

    if args.test_mic:
        for _ in range(6):
            pcm = cam.fetch_mic(1000)
            if pcm is not None and len(pcm):
                rms = float(np.sqrt(np.mean(pcm.astype(np.float32) ** 2)))
                peak = float(np.max(np.abs(pcm)))
                print(f"[mic] samples={len(pcm)} rms={rms:.1f} peak={peak} level={'🔊' if rms > 300 else '🔇'}")
            time.sleep(0.4)
        return 0

    wake_loop(cam, once=args.once)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nBye.")
        sys.exit(0)
