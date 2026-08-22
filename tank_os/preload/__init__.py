"""
TankOS Preload — Complete Offline Dependency Preloading System.

This package provides the manifest, download engine, and verification
tools to ensure TankOS functions completely offline.

Modules:
    manifest    — Dependency definitions, categories, and queries
    downloader  — Robust download engine with resume, checksums, install
    (used by)   tank_os.core.preload_manager — Orchestrator singleton
"""
