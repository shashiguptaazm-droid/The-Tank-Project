"""TankOS VNC Launcher — runs TankOS GUI persistently on display :99.

Usage::

    DISPLAY=:99 TANKOS_QT=1 python3 tank_os/startup/vnc_launcher.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

os.environ.setdefault('TANKOS_QT', '1')
os.environ.setdefault('QT_QPA_PLATFORM', 'xcb')

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

from tank_os.shell.main import main, TankShell

print('TankOS VNC Launcher starting...', flush=True)

# Delegate to TankShell main — it handles QApplication creation internally
sys.exit(main())
