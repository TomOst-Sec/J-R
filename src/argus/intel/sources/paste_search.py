"""Public paste search source."""

from __future__ import annotations

from argus.intel.base import BaseIntelSource
from argus.models.intel import IntelResult, IntelSelector, SelectorType

_SUPPORTED = {SelectorType.EMAIL, SelectorType.USERNAME}


class PasteSearchSource(BaseIntelSource):
    name = "paste_search"
    source_type = "identity"
    requires_api_key = False
    rate_limit_per_minute = 10

    async def query(self, selector: IntelSelector) -> list[IntelResult]:
        if selector.selector_type not in _SUPPORTED:
            return []

        query = selector.value
        url = f"https://psbdmp.ws/api/v3/search/{query}"

        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    return []
                body = await resp.json()

                pastes = []
                if isinstance(body, list):
                    pastes = body
                elif isinstance(body, dict):
                    pastes = body.get("data", body.get("results", []))

                return [
                    IntelResult(
                        source=self.name,
                        source_type=self.source_type,
                        data={
                            "query": query,
                            "paste_count": len(pastes),
                            "pastes": [
                                {
                                    "id": p.get("id"),
                                    "tags": p.get("tags"),
                                    "time": p.get("time"),
                                    "length": p.get("length"),
                                }
                                for p in (pastes[:20] if isinstance(pastes, list) else [])
                            ],
                        },
                        confidence=0.7 if pastes else 0.2,
                        raw=body if pastes else None,
                    )
                ]
        except Exception:
            return []
