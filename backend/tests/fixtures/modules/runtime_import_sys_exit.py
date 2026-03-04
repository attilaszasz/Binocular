"""Test fixture module that calls sys.exit() during import."""

from __future__ import annotations

import sys

sys.exit(2)
