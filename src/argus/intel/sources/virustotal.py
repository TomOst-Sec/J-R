"""VirusTotal domain and IP intelligence source."""

from __future__ import annotations

from argus.intel.base import BaseIntelSource
from argus.models.intel import IntelResult, IntelSelector, SelectorType

_SUPPORTED = {SelectorType.DOMAIN, SelectorType.IP}


class VirusTotalSource(BaseIntelSource):
    name = "virustotal"
    source_type = "network"
    requires_api_key = True
    rate_limit_per_minute = 4

    async def query(self, selector: IntelSelector) -> list[IntelResult]:
        if selector.selector_type not in _SUPPORTED:
            return []

        api_key = self._get_api_key()
        if not api_key:
            return []

        headers = {"x-apikey": api_key}

        try:
            if selector.selector_type == SelectorType.DOMAIN:
                url = f"https://www.virustotal.com/api/v3/domains/{selector.value}"
            else:
                url = f"https://www.virustotal.com/api/v3/ip_addresses/{selector.value}"

            async with self.session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    return []
                body = await resp.json()
                attrs = body.get("data", {}).get("attributes", {})
                analysis = attrs.get("last_analysis_stats", {})

                return [
                    IntelResult(
                        source=self.name,
                        source_type=self.source_type,
                        data={
                            "target": selector.value,
                            "type": selector.selector_type.value,
                            "reputation": attrs.get("reputation"),
                            "analysis_stats": analysis,
                            "categories": attrs.get("categories", {}),
                            "registrar": attrs.get("registrar"),
                            "creation_date": attrs.get("creation_date"),
                            "whois": attrs.get("whois"),
                            "last_analysis_date": attrs.get("last_analysis_date"),
                            "tags": attrs.get("tags", []),
                        },
                        confidence=0.9,
                        raw=body,
                    )
                ]
        except Exception:
            return []
