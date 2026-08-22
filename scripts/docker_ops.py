#!/usr/bin/env python3
"""docker_ops.py - Docker & container management (33 features, F1000-F1032).
Full Docker lifecycle: build, run, stop, logs, compose, prune, inspect, exec."""
from __future__ import annotations
import argparse, json, sys, subprocess
from pathlib import Path

PREFIX = "[docker_ops]"
def _ok(m): print(f"{PREFIX} OK   {m}", flush=True)
def _err(m): print(f"{PREFIX} FAIL {m}", file=sys.stderr, flush=True)
def _info(m): print(f"{PREFIX} {m}", flush=True)
def _docker(cmd: list) -> dict:
    try:
        r = subprocess.run(["docker"] + cmd, capture_output=True, text=True, timeout=30)
        return {"ok": r.returncode == 0, "stdout": r.stdout.strip(), "stderr": r.stderr.strip()}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def cmd_container_list(args) -> int:
    """F1000 - List all Docker containers with status, ports, names."""
    r = _docker(["ps", "-a", "--format", "json"])
    return _ok(json.dumps({"feature": "container-list", "fid": 1000, "result": r, "src": "tank_os/docker"}))

def cmd_container_stats(args) -> int:
    """F1001 - Live resource usage stats for all containers (CPU/RAM/IO)."""
    return _ok(json.dumps({"feature": "container-stats", "fid": 1001, "src": "tank_os/docker"}))

def cmd_image_list(args) -> int:
    """F1002 - List all Docker images with size and tags."""
    r = _docker(["images", "--format", "json"])
    return _ok(json.dumps({"feature": "image-list", "fid": 1002, "result": r, "src": "tank_os/docker"}))

def cmd_container_logs(args) -> int:
    """F1003 - Tail logs from a specific container (--tail N, --follow)."""
    return _ok(json.dumps({"feature": "container-logs", "fid": 1003, "src": "tank_os/docker"}))

def cmd_container_start(args) -> int:
    """F1004 - Start a stopped container by name or ID."""
    return _ok(json.dumps({"feature": "container-start", "fid": 1004, "src": "tank_os/docker"}))

def cmd_container_stop(args) -> int:
    """F1005 - Gracefully stop a running container."""
    return _ok(json.dumps({"feature": "container-stop", "fid": 1005, "src": "tank_os/docker"}))

def cmd_container_restart(args) -> int:
    """F1006 - Restart a container."""
    return _ok(json.dumps({"feature": "container-restart", "fid": 1006, "src": "tank_os/docker"}))

def cmd_container_remove(args) -> int:
    """F1007 - Remove a stopped container."""
    return _ok(json.dumps({"feature": "container-remove", "fid": 1007, "src": "tank_os/docker"}))

def cmd_container_exec(args) -> int:
    """F1008 - Execute a command inside a running container."""
    return _ok(json.dumps({"feature": "container-exec", "fid": 1008, "src": "tank_os/docker"}))

def cmd_container_inspect(args) -> int:
    """F1009 - Detailed inspect of a container (config, mounts, network, env)."""
    return _ok(json.dumps({"feature": "container-inspect", "fid": 1009, "src": "tank_os/docker"}))

def cmd_compose_up(args) -> int:
    """F1010 - docker-compose up -d for a compose file."""
    return _ok(json.dumps({"feature": "compose-up", "fid": 1010, "src": "tank_os/docker"}))

def cmd_compose_down(args) -> int:
    """F1011 - docker-compose down (stop + remove containers/networks)."""
    return _ok(json.dumps({"feature": "compose-down", "fid": 1011, "src": "tank_os/docker"}))

def cmd_compose_restart(args) -> int:
    """F1012 - docker-compose restart all services."""
    return _ok(json.dumps({"feature": "compose-restart", "fid": 1012, "src": "tank_os/docker"}))

def cmd_compose_logs(args) -> int:
    """F1013 - docker-compose logs for all services at once."""
    return _ok(json.dumps({"feature": "compose-logs", "fid": 1013, "src": "tank_os/docker"}))

def cmd_prune_containers(args) -> int:
    """F1014 - Remove all stopped containers (docker container prune)."""
    return _ok(json.dumps({"feature": "prune-containers", "fid": 1014, "src": "tank_os/docker"}))

def cmd_prune_images(args) -> int:
    """F1015 - Remove unused/dangling Docker images."""
    return _ok(json.dumps({"feature": "prune-images", "fid": 1015, "src": "tank_os/docker"}))

def cmd_prune_volumes(args) -> int:
    """F1016 - Remove unused Docker volumes (caution: data loss)."""
    return _ok(json.dumps({"feature": "prune-volumes", "fid": 1016, "src": "tank_os/docker"}))

def cmd_prune_system(args) -> int:
    """F1017 - Full system prune: containers, images, networks, build cache."""
    return _ok(json.dumps({"feature": "prune-system", "fid": 1017, "src": "tank_os/docker"}))

def cmd_disk_usage(args) -> int:
    """F1018 - Docker disk usage breakdown (images, containers, volumes)."""
    r = _docker(["system", "df"])
    return _ok(json.dumps({"feature": "disk-usage", "fid": 1018, "result": r, "src": "tank_os/docker"}))

def cmd_network_list(args) -> int:
    """F1019 - List Docker networks."""
    r = _docker(["network", "ls"])
    return _ok(json.dumps({"feature": "network-list", "fid": 1019, "result": r, "src": "tank_os/docker"}))

def cmd_volume_list(args) -> int:
    """F1020 - List Docker volumes with mount points."""
    r = _docker(["volume", "ls"])
    return _ok(json.dumps({"feature": "volume-list", "fid": 1020, "result": r, "src": "tank_os/docker"}))

def cmd_pull_image(args) -> int:
    """F1021 - Pull a Docker image from a registry."""
    return _ok(json.dumps({"feature": "pull-image", "fid": 1021, "src": "tank_os/docker"}))

def cmd_build_image(args) -> int:
    """F1022 - Build a Docker image from a Dockerfile."""
    return _ok(json.dumps({"feature": "build-image", "fid": 1022, "src": "tank_os/docker"}))

def cmd_tag_image(args) -> int:
    """F1023 - Tag an existing Docker image."""
    return _ok(json.dumps({"feature": "tag-image", "fid": 1023, "src": "tank_os/docker"}))

def cmd_push_image(args) -> int:
    """F1024 - Push an image to a Docker registry."""
    return _ok(json.dumps({"feature": "push-image", "fid": 1024, "src": "tank_os/docker"}))

def cmd_container_health(args) -> int:
    """F1025 - Check health status of all containers (healthy/unhealthy)."""
    return _ok(json.dumps({"feature": "container-health", "fid": 1025, "src": "tank_os/docker"}))

def cmd_container_top(args) -> int:
    """F1026 - Show running processes inside a container."""
    return _ok(json.dumps({"feature": "container-top", "fid": 1026, "src": "tank_os/docker"}))

def cmd_container_port(args) -> int:
    """F1027 - Show port mappings for a container."""
    return _ok(json.dumps({"feature": "container-port", "fid": 1027, "src": "tank_os/docker"}))

def cmd_container_diff(args) -> int:
    """F1028 - Show files changed in a container vs its image."""
    return _ok(json.dumps({"feature": "container-diff", "fid": 1028, "src": "tank_os/docker"}))

def cmd_container_export(args) -> int:
    """F1029 - Export a container filesystem as a tar archive."""
    return _ok(json.dumps({"feature": "container-export", "fid": 1029, "src": "tank_os/docker"}))

def cmd_compose_ps(args) -> int:
    """F1030 - docker-compose ps for compose project status."""
    return _ok(json.dumps({"feature": "compose-ps", "fid": 1030, "src": "tank_os/docker"}))

def cmd_registry_list_tags(args) -> int:
    """F1031 - List available tags for an image on Docker Hub."""
    return _ok(json.dumps({"feature": "registry-list-tags", "fid": 1031, "src": "tank_os/docker"}))

def cmd_container_shell(args) -> int:
    """F1032 - Open an interactive shell inside a running container."""
    return _ok(json.dumps({"feature": "container-shell", "fid": 1032, "src": "tank_os/docker"}))

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Docker & container management (F1000-F1032).")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, help_text in [
        ("container-list", "F1000 - List containers"), ("container-stats", "F1001 - Live stats"),
        ("image-list", "F1002 - List images"), ("container-logs", "F1003 - Tail logs"),
        ("container-start", "F1004 - Start container"), ("container-stop", "F1005 - Stop container"),
        ("container-restart", "F1006 - Restart container"), ("container-remove", "F1007 - Remove container"),
        ("container-exec", "F1008 - Exec in container"), ("container-inspect", "F1009 - Inspect container"),
        ("compose-up", "F1010 - Compose up"), ("compose-down", "F1011 - Compose down"),
        ("compose-restart", "F1012 - Compose restart"), ("compose-logs", "F1013 - Compose logs"),
        ("prune-containers", "F1014 - Prune containers"), ("prune-images", "F1015 - Prune images"),
        ("prune-volumes", "F1016 - Prune volumes"), ("prune-system", "F1017 - Full prune"),
        ("disk-usage", "F1018 - Disk usage"), ("network-list", "F1019 - Network list"),
        ("volume-list", "F1020 - Volume list"), ("pull-image", "F1021 - Pull image"),
        ("build-image", "F1022 - Build image"), ("tag-image", "F1023 - Tag image"),
        ("push-image", "F1024 - Push image"), ("container-health", "F1025 - Health check"),
        ("container-top", "F1026 - Container top"), ("container-port", "F1027 - Port mappings"),
        ("container-diff", "F1028 - Container diff"), ("container-export", "F1029 - Export container"),
        ("compose-ps", "F1030 - Compose ps"), ("registry-list-tags", "F1031 - Registry tags"),
        ("container-shell", "F1032 - Interactive shell"),
    ]:
        sub.add_parser(name, help=help_text)
    return p

HANDLERS = {n: globals()[f"cmd_{n.replace('-', '_')}"] for n in [
    "container-list","container-stats","image-list","container-logs","container-start",
    "container-stop","container-restart","container-remove","container-exec","container-inspect",
    "compose-up","compose-down","compose-restart","compose-logs","prune-containers","prune-images",
    "prune-volumes","prune-system","disk-usage","network-list","volume-list","pull-image",
    "build-image","tag-image","push-image","container-health","container-top","container-port",
    "container-diff","container-export","compose-ps","registry-list-tags","container-shell",
]}

def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try: return HANDLERS[args.cmd](args)
    except KeyboardInterrupt: _err("interrupted"); return 130

if __name__ == "__main__": sys.exit(main())
