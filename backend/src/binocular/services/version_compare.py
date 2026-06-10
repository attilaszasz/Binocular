"""Version comparison service for diverse firmware version formats."""

from __future__ import annotations

import re
from typing import Any


class VersionCompare:
    """Tolerant hybrid parser and comparator for firmware version strings."""

    @staticmethod
    def _parse(v: str) -> list[tuple[int, Any]]:
        # Strip leading v, V, ver, Ver
        v_clean = re.sub(
            r"^(version|ver|v)\s*[-_.]*", "", v.strip(), flags=re.IGNORECASE
        )
        # Find all tokens: either integer sequences or alphabetic sequences
        tokens = re.findall(r"(\d+|[a-zA-Z]+)", v_clean)
        parsed = []
        for token in tokens:
            if token.isdigit():
                parsed.append((0, int(token)))  # 0 indicates numeric token
            else:
                parsed.append((1, token.lower()))  # 1 indicates alphabetic token
        return parsed

    @classmethod
    def compare(cls, v1: str, v2: str) -> int:
        """Compare two version strings v1 and v2.

        Returns:
            - Positive value if v2 > v1 (v2 is newer)
            - Negative value if v2 < v1 (v2 is older/rollback)
            - 0 if v2 == v1
        """
        # Clean whitespaces
        v1 = v1.strip()
        v2 = v2.strip()

        if v1 == v2:
            return 0

        p1 = cls._parse(v1)
        p2 = cls._parse(v2)

        # If one of them has no tokens, do string comparison
        if not p1 or not p2:
            if v1 == v2:
                return 0
            return 1 if v2 > v1 else -1

        pre_releases = {"alpha", "beta", "rc", "pre", "dev"}

        for t1, t2 in zip(p1, p2, strict=False):
            if t1[0] == 0 and t2[0] == 0:
                # both numeric
                if t1[1] != t2[1]:
                    return 1 if t2[1] > t1[1] else -1
            elif t1[0] == 1 and t2[0] == 1:
                # both alphabetic
                is_pre1 = t1[1] in pre_releases
                is_pre2 = t2[1] in pre_releases
                if is_pre1 and not is_pre2:
                    return 1  # t2 is release, t1 is pre-release -> t2 > t1
                elif not is_pre1 and is_pre2:
                    return -1  # t1 is release, t2 is pre-release -> t2 < t1
                else:
                    if t1[1] != t2[1]:
                        return 1 if t2[1] > t1[1] else -1
            else:
                # one numeric, one alphabetic
                if t1[0] == 0:  # t1 is numeric, t2 is alpha
                    if t2[1] in pre_releases:
                        return -1  # t1 (numeric release) > t2 (pre-release)
                    else:
                        return 1  # t2 (suffix update, e.g. 1a) > t1 (1)
                else:  # t1 is alpha, t2 is numeric
                    if t1[1] in pre_releases:
                        return 1  # t2 (numeric release) > t1 (pre-release)
                    else:
                        return -1  # t1 (suffix update, e.g. 1a) > t2 (1)

        # If all zipped parts are equal, the longer one is newer unless
        # the remaining parts are pre-releases
        if len(p2) > len(p1):
            for t in p2[len(p1) :]:
                if t[0] == 1 and t[1] in pre_releases:
                    return -1  # v2 is pre-release, so v1 is newer
            return 1
        elif len(p1) > len(p2):
            for t in p1[len(p2) :]:
                if t[0] == 1 and t[1] in pre_releases:
                    return 1  # v1 is pre-release, so v2 is newer
            return -1

        return 0

    @classmethod
    def is_newer(cls, current: str, latest: str) -> bool:
        """Return True if latest is newer than current, False otherwise."""
        return cls.compare(current, latest) > 0
