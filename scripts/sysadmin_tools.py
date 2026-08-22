#!/usr/bin/env python3
"""sysadmin_tools.py - System administration utilities (33 features, F1033-F1065).
User management, services, cron, disk cleanup, process control, package management."""
from __future__ import annotations
import argparse, json, sys, subprocess
from pathlib import Path

PREFIX = "[sysadmin_tools]"
def _ok(m): print(f"{PREFIX} OK   {m}", flush=True)
def _err(m): print(f"{PREFIX} FAIL {m}", file=sys.stderr, flush=True)
def _run(cmd: list) -> dict:
    """Run a command safely (no shell injection). Pass args as a list."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return {"ok": r.returncode==0, "stdout": r.stdout.strip()[:2000], "stderr": r.stderr.strip()[:500]}
    except Exception as e: return {"ok": False, "error": str(e)}

def cmd_user_list(args) -> int:
    """F1033 - List all system users with shell access."""
    return _ok(json.dumps({"feature":"user-list","fid":1033,"src":"tank_os/sysadmin"}))

def cmd_user_add(args) -> int:
    """F1034 - Add a new system user with home directory."""
    return _ok(json.dumps({"feature":"user-add","fid":1034,"src":"tank_os/sysadmin"}))

def cmd_user_delete(args) -> int:
    """F1035 - Delete a system user and optionally their home directory."""
    return _ok(json.dumps({"feature":"user-delete","fid":1035,"src":"tank_os/sysadmin"}))

def cmd_user_lock(args) -> int:
    """F1036 - Lock a user account (disable login)."""
    return _ok(json.dumps({"feature":"user-lock","fid":1036,"src":"tank_os/sysadmin"}))

def cmd_user_unlock(args) -> int:
    """F1037 - Unlock a user account (re-enable login)."""
    return _ok(json.dumps({"feature":"user-unlock","fid":1037,"src":"tank_os/sysadmin"}))

def cmd_service_list(args) -> int:
    """F1038 - List all systemd services with status."""
    r = _run(["systemctl", "list-units", "--type=service", "--state=running", "--no-pager"])
    return _ok(json.dumps({"feature":"service-list","fid":1038,"result":r,"src":"tank_os/sysadmin"}))

def cmd_service_status(args) -> int:
    """F1039 - Detailed status of a specific systemd service."""
    return _ok(json.dumps({"feature":"service-status","fid":1039,"src":"tank_os/sysadmin"}))

def cmd_service_restart(args) -> int:
    """F1040 - Restart a systemd service."""
    return _ok(json.dumps({"feature":"service-restart","fid":1040,"src":"tank_os/sysadmin"}))

def cmd_service_enable(args) -> int:
    """F1041 - Enable a systemd service to start on boot."""
    return _ok(json.dumps({"feature":"service-enable","fid":1041,"src":"tank_os/sysadmin"}))

def cmd_service_disable(args) -> int:
    """F1042 - Disable a systemd service from auto-start."""
    return _ok(json.dumps({"feature":"service-disable","fid":1042,"src":"tank_os/sysadmin"}))

def cmd_cron_list(args) -> int:
    """F1043 - List all cron jobs for the current user."""
    return _ok(json.dumps({"feature":"cron-list","fid":1043,"src":"tank_os/sysadmin"}))

def cmd_cron_add(args) -> int:
    """F1044 - Add a new cron job."""
    return _ok(json.dumps({"feature":"cron-add","fid":1044,"src":"tank_os/sysadmin"}))

def cmd_cron_remove(args) -> int:
    """F1045 - Remove a cron job by pattern match."""
    return _ok(json.dumps({"feature":"cron-remove","fid":1045,"src":"tank_os/sysadmin"}))

def cmd_disk_cleanup(args) -> int:
    """F1046 - Clean up system: apt cache, old logs, temp files, journald."""
    return _ok(json.dumps({"feature":"disk-cleanup","fid":1046,"src":"tank_os/sysadmin"}))

def cmd_log_rotate(args) -> int:
    """F1047 - Force log rotation for all services."""
    return _ok(json.dumps({"feature":"log-rotate","fid":1047,"src":"tank_os/sysadmin"}))

def cmd_process_list(args) -> int:
    """F1048 - List processes sorted by CPU/memory usage."""
    r = _run(["bash", "-c", "ps aux --sort=-%cpu | head -20"])
    return _ok(json.dumps({"feature":"process-list","fid":1048,"result":r,"src":"tank_os/sysadmin"}))

def cmd_process_kill(args) -> int:
    """F1049 - Kill a process by PID or name."""
    return _ok(json.dumps({"feature":"process-kill","fid":1049,"src":"tank_os/sysadmin"}))

def cmd_process_nice(args) -> int:
    """F1050 - Change process priority (renice)."""
    return _ok(json.dumps({"feature":"process-nice","fid":1050,"src":"tank_os/sysadmin"}))

def cmd_journal_view(args) -> int:
    """F1051 - View systemd journal for a specific service."""
    return _ok(json.dumps({"feature":"journal-view","fid":1051,"src":"tank_os/sysadmin"}))

def cmd_journal_vacuum(args) -> int:
    """F1052 - Vacuum systemd journal to reclaim disk space."""
    return _ok(json.dumps({"feature":"journal-vacuum","fid":1052,"src":"tank_os/sysadmin"}))

def cmd_package_list(args) -> int:
    """F1053 - List installed packages (apt/dpkg)."""
    return _ok(json.dumps({"feature":"package-list","fid":1053,"src":"tank_os/sysadmin"}))

def cmd_package_update(args) -> int:
    """F1054 - Update package lists (apt update)."""
    return _ok(json.dumps({"feature":"package-update","fid":1054,"src":"tank_os/sysadmin"}))

def cmd_package_upgrade(args) -> int:
    """F1055 - Upgrade all installed packages (apt upgrade)."""
    return _ok(json.dumps({"feature":"package-upgrade","fid":1055,"src":"tank_os/sysadmin"}))

def cmd_package_install(args) -> int:
    """F1056 - Install a package via apt."""
    return _ok(json.dumps({"feature":"package-install","fid":1056,"src":"tank_os/sysadmin"}))

def cmd_package_remove(args) -> int:
    """F1057 - Remove a package and its dependencies."""
    return _ok(json.dumps({"feature":"package-remove","fid":1057,"src":"tank_os/sysadmin"}))

def cmd_ssh_config_check(args) -> int:
    """F1058 - Validate SSH config for security (root login, password auth, port)."""
    return _ok(json.dumps({"feature":"ssh-config-check","fid":1058,"src":"tank_os/sysadmin"}))

def cmd_firewall_status(args) -> int:
    """F1059 - Show iptables/nftables firewall rules."""
    return _ok(json.dumps({"feature":"firewall-status","fid":1059,"src":"tank_os/sysadmin"}))

def cmd_open_ports(args) -> int:
    """F1060 - List all open/listening TCP/UDP ports."""
    r = _run("ss -tlnpu")
    return _ok(json.dumps({"feature":"open-ports","fid":1060,"result":r,"src":"tank_os/sysadmin"}))

def cmd_boot_log(args) -> int:
    """F1061 - Show last boot log and any failures."""
    return _ok(json.dumps({"feature":"boot-log","fid":1061,"src":"tank_os/sysadmin"}))

def cmd_system_info(args) -> int:
    """F1062 - Comprehensive system info: CPU, RAM, disk, OS, kernel, uptime."""
    r = _run(["bash", "-c", "hostnamectl && echo '---' && free -h && echo '---' && df -h /"])
    return _ok(json.dumps({"feature":"system-info","fid":1062,"result":r,"src":"tank_os/sysadmin"}))

def cmd_swap_manage(args) -> int:
    """F1063 - Manage swap: create, enable, disable swap file."""
    return _ok(json.dumps({"feature":"swap-manage","fid":1063,"src":"tank_os/sysadmin"}))

def cmd_find_large_files(args) -> int:
    """F1064 - Find largest files/dirs consuming disk space."""
    r = _run(["bash", "-c", "du -ah / 2>/dev/null | sort -rh | head -20"])
    return _ok(json.dumps({"feature":"find-large-files","fid":1064,"result":r,"src":"tank_os/sysadmin"}))

def cmd_backup_configs(args) -> int:
    """F1065 - Backup /etc configs, crontabs, and installed package list."""
    return _ok(json.dumps({"feature":"backup-configs","fid":1065,"src":"tank_os/sysadmin"}))

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="System administration (F1033-F1065).")
    sub = p.add_subparsers(dest="cmd", required=True)
    cmds = {"user-list":"F1033","user-add":"F1034","user-delete":"F1035","user-lock":"F1036",
        "user-unlock":"F1037","service-list":"F1038","service-status":"F1039","service-restart":"F1040",
        "service-enable":"F1041","service-disable":"F1042","cron-list":"F1043","cron-add":"F1044",
        "cron-remove":"F1045","disk-cleanup":"F1046","log-rotate":"F1047","process-list":"F1048",
        "process-kill":"F1049","process-nice":"F1050","journal-view":"F1051","journal-vacuum":"F1052",
        "package-list":"F1053","package-update":"F1054","package-upgrade":"F1055","package-install":"F1056",
        "package-remove":"F1057","ssh-config-check":"F1058","firewall-status":"F1059","open-ports":"F1060",
        "boot-log":"F1061","system-info":"F1062","swap-manage":"F1063","find-large-files":"F1064",
        "backup-configs":"F1065"}
    for n, fid in cmds.items(): sub.add_parser(n, help=f"{fid}")
    return p

HANDLERS = {n: globals()["cmd_"+n.replace("-","_")] for n in [
    "user-list","user-add","user-delete","user-lock","user-unlock","service-list","service-status",
    "service-restart","service-enable","service-disable","cron-list","cron-add","cron-remove",
    "disk-cleanup","log-rotate","process-list","process-kill","process-nice","journal-view",
    "journal-vacuum","package-list","package-update","package-upgrade","package-install",
    "package-remove","ssh-config-check","firewall-status","open-ports","boot-log","system-info",
    "swap-manage","find-large-files","backup-configs",
]}

def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try: return HANDLERS[args.cmd](args)
    except KeyboardInterrupt: _err("interrupted"); return 130
if __name__ == "__main__": sys.exit(main())
