"""DNS record lookup source using Google DNS-over-HTTPS."""

from __future__ import annotations

from argus.intel.base import BaseIntelSource
from argus.models.intel import IntelResult, IntelSelector, SelectorType

_RECORD_TYPES = ("A", "AAAA", "MX", "TXT", "NS")


class DNSSource(BaseIntelSource):
    name = "dns"
    source_type = "dns"
    requires_api_key = False
    rate_limit_per_minute = 60

    async def query(self, selector: IntelSelector) -> list[IntelResult]:
        if selector.selector_type != SelectorType.DOMAIN:
            return []

        domain = selector.value
        records: dict[str, list] = {}

        try:
            for rtype in _RECORD_TYPES:
                url = "https://dns.google/resolve"
                params = {"name": domain, "type": rtype}
                try:
                    async with self.session.get(url, params=params) as resp:
                        if resp.status != 200:
                            continue
                        body = await resp.json()
                        answers = body.get("Answer", [])
                        if rtype == "MX":
                            records["mx"] = [
                                {"priority": a.get("data", "").split()[0] if " " in a.get("data", "") else "",
                                 "exchange": a.get("data", "").split()[-1]}
                                for a in answers
                            ]
                        else:
                            records[rtype.lower()] = [a.get("data", "") for a in answers]
                except Exception:
                    continue

            return [
                IntelResult(
                    source=self.name,
                    source_type=self.source_type,
                    data={
                        "domain": domain,
                        "a": records.get("a", []),
                        "aaaa": records.get("aaaa", []),
                        "mx": records.get("mx", []),
                        "txt": records.get("txt", []),
                        "ns": records.get("ns", []),
                    },
                    confidence=0.95,
                )
            ]
        except Exception:
            return []
