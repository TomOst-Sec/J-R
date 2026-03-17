"""Libravatar avatar lookup source."""

from __future__ import annotations

import hashlib

from argus.intel.base import BaseIntelSource
from argus.models.intel import IntelResult, IntelSelector, SelectorType


class LibravatarSource(BaseIntelSource):
    name = "libravatar"
    source_type = "identity"
    requires_api_key = False
    rate_limit_per_minute = 30

    async def query(self, selector: IntelSelector) -> list[IntelResult]:
        if selector.selector_type != SelectorType.EMAIL:
            return []

        email = selector.value.strip().lower()
        md5 = hashlib.md5(email.encode()).hexdigest()  # noqa: S324
        avatar_url = f"https://seccdn.libravatar.org/avatar/{md5}?d=404"

        try:
            async with self.session.get(avatar_url) as resp:
                has_avatar = resp.status == 200
                return [
                    IntelResult(
                        source=self.name,
                        source_type=self.source_type,
                        data={
                            "email": selector.value,
                            "has_avatar": has_avatar,
                            "avatar_url": avatar_url.replace("?d=404", "") if has_avatar else None,
                            "md5_hash": md5,
                        },
                        confidence=0.7 if has_avatar else 0.3,
                    )
                ]
        except Exception:
            return []
