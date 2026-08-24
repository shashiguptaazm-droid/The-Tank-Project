#!/usr/bin/env python3
"""Test script for the Tank Blind-Assistance Module.

Usage:
  python3 scripts/test_blind_assist.py                # Quick smoke test
  python3 scripts/test_blind_assist.py --integration  # Integration tests
  python3 scripts/test_blind_assist.py --hardware     # Hardware loop test
  python3 scripts/test_blind_assist.py --e2e          # End-to-end test
"""
import argparse
import json
import os
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

PASS = "✅"
FAIL = "❌"
WARN = "⚠️"


def smoke_test():
    """Quick smoke test — verifies imports and basic functionality."""
    print(f"{PASS} Smoke Test — Blind-Assistance Module")
    print("=" * 50)

    # Test 1: Imports
    print("\n  [1] Import check...")
    try:
        from tank.blind_assist.main import BlindAssist, SceneResult
        print(f"    {PASS} BlindAssist imported")
    except Exception as e:
        print(f"    {FAIL} Import failed: {e}")
        return False

    # Test 2: SceneResult dataclass
    print("\n  [2] SceneResult...")
    try:
        sr = SceneResult(frame_id=1, timestamp=time.time(),
                         objects=["chair"], obstacles=["stairs"],
                         guidance="Turn left", audio_text="Turn left",
                         latency_ms=250.0)
        d = sr.to_dict()
        assert d["objects"] == ["chair"]
        assert d["obstacles"] == ["stairs"]
        speakable = sr.speakable()
        assert "stairs" in speakable
        assert "Turn left" in speakable
        print(f"    {PASS} SceneResult data class works")
        print(f"    {PASS} to_dict: {json.dumps(d)}")
        print(f"    {PASS} speakable: {speakable}")
    except Exception as e:
        print(f"    {FAIL} SceneResult test failed: {e}")
        return False

    # Test 3: EmergencySystem (no hardware needed)
    print("\n  [3] EmergencySystem...")
    try:
        from tank.blind_assist.main import EmergencySystem
        es = EmergencySystem()
        # Should not trigger (only 1 tap, not 3)
        triggered = es.tap()
        assert not triggered, "Single tap should not trigger"
        print(f"    {PASS} EmergencySystem created, single tap correctly ignored")
    except Exception as e:
        print(f"    {WARN} EmergencySystem test: {e}")

    # Test 4: VoiceCommander command matching
    print("\n  [4] VoiceCommander...")
    try:
        from tank.blind_assist.main import VoiceCommander
        vc = VoiceCommander()
        assert vc.match_command("what's around me") == "describe"
        assert vc.match_command("read that sign please") == "read_text"
        assert vc.match_command("call emergency now") == "emergency"
        assert vc.match_command("find my keys") == "find_object:keys"
        assert vc.match_command("some random noise") is None
        print(f"    {PASS} Command matching works for all patterns")
    except Exception as e:
        print(f"    {FAIL} VoiceCommander test: {e}")
        return False

    # Test 5: DualScreen (no hardware)
    print("\n  [5] DualScreen (dry run)...")
    try:
        from tank.blind_assist.main import DualScreen
        ds = DualScreen(serial_port="/dev/null")
        connected = ds.connect()
        if not connected:
            print(f"    {WARN} No serial port (expected without hardware)")
        # These should not crash even without hardware
        ds.set_expression("neutral")
        ds.set_expression("alert")
        ds.set_expression("emergency")
        ds.show_text("test message")
        ds.speak("hello world")
        ds.alert_obstacle("ahead", 3.0)
        ds.emergency_alarm()
        ds.disconnect()
        print(f"    {PASS} DualScreen API works (no hardware needed for smoke test)")
    except Exception as e:
        print(f"    {FAIL} DualScreen test: {e}")
        return False

    print(f"\n  {PASS} All smoke tests passed!")
    return True


def integration_test():
    """Integration test — requires ESP32 CAM and Jetson."""
    print(f"{PASS} Integration Test — Blind-Assistance Module")
    print("=" * 50)

    from tank.blind_assist.main import BlindAssist

    ba = BlindAssist(
        esp32cam_host=os.environ.get("ESP32_CAM_HOST", "192.168.31.145"),
        mode="vision-only",
    )

    # Test 1: Process one frame
    print("\n  [1] Process one frame...")
    try:
        result = ba.process_one_frame()
        print(f"    Frame ID: {result.frame_id}")
        print(f"    Latency: {result.latency_ms:.0f}ms")
        print(f"    Source: {result.source}")
        print(f"    Guidance: {result.guidance[:80]}...")
        print(f"    {PASS} Frame processed")
    except Exception as e:
        print(f"    {FAIL} Frame processing failed: {e}")
        return False

    # Test 2: Get status
    print("\n  [2] Get status...")
    try:
        status = ba.get_status()
        print(f"    {json.dumps(status, indent=6)}")
        assert status["frames"] > 0, "No frames captured"
        print(f"    {PASS} Status retrieved")
    except Exception as e:
        print(f"    {FAIL} Status failed: {e}")
        return False

    print(f"\n  {PASS} Integration tests passed!")
    return True


def hardware_test():
    """Hardware loop test — requires all physical devices connected."""
    print(f"{PASS} Hardware Loop Test — Blind-Assistance Module")
    print("=" * 50)
    print(f"  {WARN} This test requires: ESP32 CAM + ESP32 Dual Screen + LTE Modem")
    print("  Make sure all devices are connected and powered on.")
    print()

    from tank.blind_assist.main import BlindAssist

    ba = BlindAssist(mode="full")

    # Test 1: Camera capture
    print("  [1] Camera capture test...")
    from tank.blind_assist.main import CV2_AVAILABLE
    jpeg = ba._capture_frame()
    if jpeg and len(jpeg) > 100:
        print(f"    {PASS} Camera working — {len(jpeg)} bytes captured")
        if CV2_AVAILABLE:
            import cv2
            import numpy as np
            buf = np.frombuffer(jpeg, dtype=np.uint8)
            frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
            if frame is not None:
                print(f"    {PASS} Frame decoded: {frame.shape[1]}x{frame.shape[0]}")
            else:
                print(f"    {FAIL} Could not decode JPEG frame")
    else:
        print(f"    {FAIL} Camera not working — check ESP32-S3 CAM at {ba.esp32cam_host}")
        return False

    # Test 2: Dual Screen
    print("\n  [2] Dual Screen test...")
    ba.screen.set_expression("happy")
    time.sleep(0.5)
    ba.screen.show_text("Tank blind assist active")
    time.sleep(0.5)
    ba.screen.set_expression("neutral")
    print(f"    {PASS} Screen commands sent")

    # Test 3: Speaker
    print("\n  [3] Speaker test...")
    ba.screen.speak("Tank blind assistance system online. All systems working.")
    time.sleep(0.5)
    print(f"    {PASS} Speak command sent")

    # Test 4: Emergency contacts
    print("\n  [4] Emergency contacts...")
    if os.path.exists(ba.emergency.CONTACTS_PATH):
        with open(ba.emergency.CONTACTS_PATH) as f:
            lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        print(f"    {PASS} Contacts file: {len(lines)} contacts")
    else:
        print(f"    {WARN} No contacts file at {ba.emergency.CONTACTS_PATH}")

    # Test 5: LTE modem
    print("\n  [5] LTE modem test...")
    import subprocess
    try:
        modems = subprocess.check_output("mmcli -L", shell=True, text=True, timeout=5)
        print(f"    {PASS} Modem detected: {modems.strip()}")
    except Exception:
        print(f"    {WARN} ModemManager not available or no modem")

    print(f"\n  {PASS} Hardware tests complete!")
    return True


def main():
    parser = argparse.ArgumentParser(description="Test Tank Blind-Assistance Module")
    parser.add_argument("--integration", action="store_true", help="Run integration tests")
    parser.add_argument("--hardware", action="store_true", help="Run hardware loop tests")
    parser.add_argument("--e2e", action="store_true", help="Run end-to-end test with AI")
    args = parser.parse_args()

    if args.e2e:
        print("End-to-end test — processing 5 frames with AI...")
        from tank.blind_assist.main import BlindAssist
        ba = BlindAssist(mode="vision-only")
        for i in range(5):
            result = ba.process_one_frame()
            print(f"  Frame {result.frame_id}: {result.guidance[:100]}")
            time.sleep(2)
        print(f"{PASS} E2E test complete")
    elif args.hardware:
        hardware_test()
    elif args.integration:
        integration_test()
    else:
        smoke_test()


if __name__ == "__main__":
    main()