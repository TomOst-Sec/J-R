"""LeakCheck breach lookup source."""

from __future__ import annotations

from argus.intel.base import BaseIntelSource
from argus.models.intel import IntelResult, IntelSelector, SelectorType


class LeakCheckSource(BaseIntelSource):
    name = "leakcheck"
    source_type = "breach"
    requires_api_key = True
    rate_limit_per_minute = 15

    async def query(self, selector: IntelSelector) -> list[IntelResult]:
        if selector.selector_type != SelectorType.EMAIL:
            return []

        api_key = self._get_api_key()
        if not api_key:
            return []

        url = "https://leakcheck.io/api/public"
        params = {"check": selector.value}
        headers = {"X-API-Key": api_key}

        try:
            async with self.session.get(url, params=params, headers=headers) as resp:
                if resp.status != 200:
                    return []
                body = await resp.json()
                found = body.get("success", False)
                sources = body.get("sources", [])
                return [
                    IntelResult(
                        source=self.name,
                        source_type=self.source_type,
                        data={
                            "email": selector.value,
                            "found": found,
                            "source_count": len(sources),
                            "sources": sources,
                        },
                        confidence=0.85 if found else 0.5,
                        raw=body,
                    )
                ]
        except Exception:
            return []
