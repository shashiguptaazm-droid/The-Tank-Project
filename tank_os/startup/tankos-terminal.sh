#!/bin/bash
# TankOS TCP Terminal — socket-activated entry point
# This is exec'd by systemd from tankos-terminal@.service
# Connects stdin/stdout to the TankOS TerminalREPL via Python

PROJECT_ROOT="/root/the tank project"
export PYTHONPATH="$PROJECT_ROOT"

exec python3 -m tank_os.shell.terminal.tcp_entry
