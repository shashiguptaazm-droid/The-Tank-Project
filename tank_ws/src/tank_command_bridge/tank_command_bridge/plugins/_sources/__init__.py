"""Per-site torrent scrapers.

Each submodule exposes:

* ``parse_<site>(html: str, query: str) -> list[TorrentHit]``
  Pure function.  No network.  Eats canned HTML fixtures so unit tests
  are hermetic.

* ``search_<site>(query: str, timeout_s: float = 6.0,
                 http_get=None) -> list[TorrentHit]``
  Thin HTTP wrapper around the parser.  ``http_get`` is an injection
  point — default is ``urllib.request.urlopen``, tests pass a stub.

All scrapers share the ``TorrentHit`` shape from
:mod:`tank_command_bridge.plugins._torrent_common`.
"""
from __future__ import annotations
