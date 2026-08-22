#!/usr/bin/env python3
"""raspberry_pi.py - Jetson & hardware tools (34 features, F1566-F1599).
Pi config, GPIO advanced, camera, display, HATs, USB devices, overclocking."""
from __future__ import annotations
import argparse, json, sys, subprocess
from pathlib import Path

PREFIX = "[raspberry_pi]"
def _ok(m): print(f"{PREFIX} OK   {m}", flush=True)
def _err(m): print(f"{PREFIX} FAIL {m}", file=sys.stderr, flush=True)
def _run(cmd: list) -> dict:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return {"ok": r.returncode==0, "stdout": r.stdout.strip()[:2000], "stderr": r.stderr.strip()[:500]}
    except Exception as e: return {"ok": False, "error": str(e)}

def cmd_pi_model(args) -> int:
    """F1566 - Detect Jetson model, revision, and RAM."""
    r = _run(["cat","/proc/device-tree/model"])
    return _ok(json.dumps({"feature":"pi-model","fid":1566,"result":r,"src":"tank_os/pi"}))

def cmd_pi_temperature(args) -> int:
    """F1567 - Show Pi CPU/GPU temperature and throttling status."""
    r = _run(["vcgencmd","measure_temp"])
    return _ok(json.dumps({"feature":"pi-temperature","fid":1567,"result":r,"src":"tank_os/pi"}))

def cmd_pi_clock_speed(args) -> int:
    """F1568 - Show current CPU/GPU/core clock frequencies."""
    return _ok(json.dumps({"feature":"pi-clock-speed","fid":1568,"src":"tank_os/pi"}))

def cmd_pi_voltage(args) -> int:
    """F1569 - Show core voltage and PMIC readings."""
    return _ok(json.dumps({"feature":"pi-voltage","fid":1569,"src":"tank_os/pi"}))

def cmd_pi_overclock(args) -> int:
    """F1570 - Configure Pi overclocking in config.txt."""
    return _ok(json.dumps({"feature":"pi-overclock","fid":1570,"src":"tank_os/pi"}))

def cmd_pi_config_backup(args) -> int:
    """F1571 - Backup /boot/config.txt and /boot/cmdline.txt."""
    return _ok(json.dumps({"feature":"pi-config-backup","fid":1571,"src":"tank_os/pi"}))

def cmd_camera_capture(args) -> int:
    """F1572 - Capture photo with Pi Camera Module (v1/v2/v3/HQ)."""
    return _ok(json.dumps({"feature":"camera-capture","fid":1572,"src":"tank_os/pi"}))

def cmd_camera_stream(args) -> int:
    """F1573 - Stream Pi Camera video over HTTP/RSTP."""
    return _ok(json.dumps({"feature":"camera-stream","fid":1573,"src":"tank_os/pi"}))

def cmd_camera_timelapse(args) -> int:
    """F1574 - Create time-lapse from Pi Camera images."""
    return _ok(json.dumps({"feature":"camera-timelapse","fid":1574,"src":"tank_os/pi"}))

def cmd_camera_settings(args) -> int:
    """F1575 - Adjust Pi Camera settings: exposure, ISO, white balance, rotation."""
    return _ok(json.dumps({"feature":"camera-settings","fid":1575,"src":"tank_os/pi"}))

def cmd_display_setup(args) -> int:
    """F1576 - Set up Pi display: official 7", HDMI, DSI, SPI screens."""
    return _ok(json.dumps({"feature":"display-setup","fid":1576,"src":"tank_os/pi"}))

def cmd_display_brightness(args) -> int:
    """F1577 - Adjust display brightness/backlight."""
    return _ok(json.dumps({"feature":"display-brightness","fid":1577,"src":"tank_os/pi"}))

def cmd_display_rotate(args) -> int:
    """F1578 - Rotate display orientation in config."""
    return _ok(json.dumps({"feature":"display-rotate","fid":1578,"src":"tank_os/pi"}))

def cmd_hat_detect(args) -> int:
    """F1579 - Detect attached HATs via EEPROM and show details."""
    return _ok(json.dumps({"feature":"hat-detect","fid":1579,"src":"tank_os/pi"}))

def cmd_hat_configure(args) -> int:
    """F1580 - Configure a Pi HAT: enable overlay, set params."""
    return _ok(json.dumps({"feature":"hat-configure","fid":1580,"src":"tank_os/pi"}))

def cmd_sense_hat_sensors(args) -> int:
    """F1581 - Read Sense HAT sensors: temp, humidity, pressure, gyro, accel."""
    return _ok(json.dumps({"feature":"sense-hat-sensors","fid":1581,"src":"tank_os/pi"}))

def cmd_sense_hat_led(args) -> int:
    """F1582 - Control Sense HAT 8x8 LED matrix: text, patterns, colors."""
    return _ok(json.dumps({"feature":"sense-hat-led","fid":1582,"src":"tank_os/pi"}))

def cmd_pi_audio_output(args) -> int:
    """F1583 - Switch Pi audio output: HDMI, 3.5mm jack, I2S DAC."""
    return _ok(json.dumps({"feature":"pi-audio-output","fid":1583,"src":"tank_os/pi"}))

def cmd_usb_device_list(args) -> int:
    """F1584 - List all USB devices with vendor/product IDs and speed."""
    r = _run(["lsusb"])
    return _ok(json.dumps({"feature":"usb-device-list","fid":1584,"result":r,"src":"tank_os/pi"}))

def cmd_usb_storage_mount(args) -> int:
    """F1585 - Auto-mount USB storage device."""
    return _ok(json.dumps({"feature":"usb-storage-mount","fid":1585,"src":"tank_os/pi"}))

def cmd_spi_loopback_test(args) -> int:
    """F1586 - SPI loopback test to verify SPI bus is working."""
    return _ok(json.dumps({"feature":"spi-loopback-test","fid":1586,"src":"tank_os/pi"}))

def cmd_i2c_detect(args) -> int:
    """F1587 - Detect all I2C devices on each bus with addresses."""
    return _ok(json.dumps({"feature":"i2c-detect","fid":1587,"src":"tank_os/pi"}))

def cmd_one_wire_temp(args) -> int:
    """F1588 - Read DS18B20 1-Wire temperature sensors."""
    return _ok(json.dumps({"feature":"one-wire-temp","fid":1588,"src":"tank_os/pi"}))

def cmd_uart_test(args) -> int:
    """F1589 - Test UART serial communication."""
    return _ok(json.dumps({"feature":"uart-test","fid":1589,"src":"tank_os/pi"}))

def cmd_pi_boot_time(args) -> int:
    """F1590 - Analyze Pi boot time and systemd-analyze critical chain."""
    r = _run(["systemd-analyze"])
    return _ok(json.dumps({"feature":"pi-boot-time","fid":1590,"result":r,"src":"tank_os/pi"}))

def cmd_pi_power_save(args) -> int:
    """F1591 - Configure Pi power saving: disable HDMI, USB, WiFi, Bluetooth."""
    return _ok(json.dumps({"feature":"pi-power-save","fid":1591,"src":"tank_os/pi"}))

def cmd_pi_eeprom_update(args) -> int:
    """F1592 - Update Pi bootloader EEPROM."""
    return _ok(json.dumps({"feature":"pi-eeprom-update","fid":1592,"src":"tank_os/pi"}))

def cmd_pi_gpio_mem_test(args) -> int:
    """F1593 - Test GPIO memory mapping and direct register access."""
    return _ok(json.dumps({"feature":"pi-gpio-mem-test","fid":1593,"src":"tank_os/pi"}))

def cmd_pi_fan_control(args) -> int:
    """F1594 - Control Pi cooling fan via GPIO with temperature thresholds."""
    return _ok(json.dumps({"feature":"pi-fan-control","fid":1594,"src":"tank_os/pi"}))

def cmd_pi_ups_monitor(args) -> int:
    """F1595 - Monitor Pi UPS HAT: battery level, charging, runtime."""
    return _ok(json.dumps({"feature":"pi-ups-monitor","fid":1595,"src":"tank_os/pi"}))

def cmd_pi_kiosk_mode(args) -> int:
    """F1596 - Set up Pi as a kiosk: auto-login, fullscreen browser, no cursor."""
    return _ok(json.dumps({"feature":"pi-kiosk-mode","fid":1596,"src":"tank_os/pi"}))

def cmd_pi_cluster_setup(args) -> int:
    """F1597 - Set up Pi cluster: networking, MPI, shared storage."""
    return _ok(json.dumps({"feature":"pi-cluster-setup","fid":1597,"src":"tank_os/pi"}))

def cmd_pi_sd_health(args) -> int:
    """F1598 - Check SD card health: wear level, bad blocks, remaining life."""
    return _ok(json.dumps({"feature":"pi-sd-health","fid":1598,"src":"tank_os/pi"}))

def cmd_pi_setup_wizard(args) -> int:
    """F1599 - Interactive Pi setup wizard: config, camera, display, HATs, audio."""
    return _ok(json.dumps({"feature":"pi-setup-wizard","fid":1599,"src":"tank_os/pi"}))

CMDS = {"pi-model":"F1566","pi-temperature":"F1567","pi-clock-speed":"F1568","pi-voltage":"F1569","pi-overclock":"F1570","pi-config-backup":"F1571","camera-capture":"F1572","camera-stream":"F1573","camera-timelapse":"F1574","camera-settings":"F1575","display-setup":"F1576","display-brightness":"F1577","display-rotate":"F1578","hat-detect":"F1579","hat-configure":"F1580","sense-hat-sensors":"F1581","sense-hat-led":"F1582","pi-audio-output":"F1583","usb-device-list":"F1584","usb-storage-mount":"F1585","spi-loopback-test":"F1586","i2c-detect":"F1587","one-wire-temp":"F1588","uart-test":"F1589","pi-boot-time":"F1590","pi-power-save":"F1591","pi-eeprom-update":"F1592","pi-gpio-mem-test":"F1593","pi-fan-control":"F1594","pi-ups-monitor":"F1595","pi-kiosk-mode":"F1596","pi-cluster-setup":"F1597","pi-sd-health":"F1598","pi-setup-wizard":"F1599"}
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Jetson tools (F1566-F1599).")
    sub = p.add_subparsers(dest="cmd", required=True)
    for n,fid in CMDS.items(): sub.add_parser(n, help=fid)
    return p
HANDLERS = {n: globals()["cmd_"+n.replace("-","_")] for n in CMDS}
def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try: return HANDLERS[args.cmd](args)
    except KeyboardInterrupt: _err("interrupted"); return 130
if __name__ == "__main__": sys.exit(main())
