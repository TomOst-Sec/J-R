"""IntelX intelligence search source."""

from __future__ import annotations

from argus.intel.base import BaseIntelSource
from argus.models.intel import IntelResult, IntelSelector, SelectorType

_SUPPORTED = {SelectorType.EMAIL, SelectorType.DOMAIN, SelectorType.IP}


class IntelXSource(BaseIntelSource):
    name = "intelx"
    source_type = "breach"
    requires_api_key = True
    rate_limit_per_minute = 10

    async def query(self, selector: IntelSelector) -> list[IntelResult]:
        if selector.selector_type not in _SUPPORTED:
            return []

        api_key = self._get_api_key()
        if not api_key:
            return []

        search_url = "https://2.intelx.io/intelligent/search"
        headers = {"x-key": api_key, "Content-Type": "application/json"}
        payload = {
            "term": selector.value,
            "maxresults": 20,
            "media": 0,
            "timeout": 10,
        }

        try:
            # Start the search
            async with self.session.post(search_url, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    return []
                search_resp = await resp.json()
                search_id = search_resp.get("id")
                if not search_id:
                    return []

            # Fetch results
            result_url = f"https://2.intelx.io/intelligent/search/result?id={search_id}"
            async with self.session.get(result_url, headers=headers) as resp:
                if resp.status != 200:
                    return []
                body = await resp.json()
                records = body.get("records", [])
                return [
                    IntelResult(
                        source=self.name,
                        source_type=self.source_type,
                        data={
                            "selector": selector.value,
                            "result_count": len(records),
                            "records": [
                                {
                                    "name": r.get("name"),
                                    "type": r.get("type"),
                                    "media": r.get("media"),
                                    "date": r.get("date"),
                                    "bucket": r.get("bucket"),
                                }
                                for r in records[:20]
                            ],
                        },
                        confidence=0.8 if records else 0.3,
                        raw=body,
                    )
                ]
        except Exception:
            return []
