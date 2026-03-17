"""crt.sh certificate transparency lookup source."""

from __future__ import annotations

from argus.intel.base import BaseIntelSource
from argus.models.intel import IntelResult, IntelSelector, SelectorType


class CrtShSource(BaseIntelSource):
    name = "crtsh"
    source_type = "cert"
    requires_api_key = False
    rate_limit_per_minute = 10

    async def query(self, selector: IntelSelector) -> list[IntelResult]:
        if selector.selector_type != SelectorType.DOMAIN:
            return []

        url = "https://crt.sh/"
        params = {"q": selector.value, "output": "json"}

        try:
            async with self.session.get(url, params=params) as resp:
                if resp.status != 200:
                    return []
                certs = await resp.json()
                if not isinstance(certs, list):
                    return []

                seen_serials: set[str] = set()
                deduped = []
                for c in certs:
                    serial = str(c.get("serial_number", ""))
                    if serial and serial in seen_serials:
                        continue
                    seen_serials.add(serial)
                    deduped.append({
                        "common_name": c.get("common_name"),
                        "issuer": c.get("issuer_name"),
                        "not_before": c.get("not_before"),
                        "not_after": c.get("not_after"),
                        "serial_number": serial,
                        "name_value": c.get("name_value"),
                    })

                return [
                    IntelResult(
                        source=self.name,
                        source_type=self.source_type,
                        data={
                            "domain": selector.value,
                            "cert_count": len(deduped),
                            "certificates": deduped[:50],
                        },
                        confidence=0.9,
                        raw={"total_raw": len(certs)},
                    )
                ]
        except Exception:
            return []
