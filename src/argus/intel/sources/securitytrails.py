"""SecurityTrails domain intelligence source."""

from __future__ import annotations

from argus.intel.base import BaseIntelSource
from argus.models.intel import IntelResult, IntelSelector, SelectorType


class SecurityTrailsSource(BaseIntelSource):
    name = "securitytrails"
    source_type = "dns"
    requires_api_key = True
    rate_limit_per_minute = 10

    async def query(self, selector: IntelSelector) -> list[IntelResult]:
        if selector.selector_type != SelectorType.DOMAIN:
            return []

        api_key = self._get_api_key()
        if not api_key:
            return []

        url = f"https://api.securitytrails.com/v1/domain/{selector.value}"
        headers = {"APIKEY": api_key, "Accept": "application/json"}

        try:
            async with self.session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    return []
                body = await resp.json()
                current_dns = body.get("current_dns", {})

                dns_data = {}
                for rtype in ("a", "aaaa", "mx", "txt", "ns", "soa"):
                    record = current_dns.get(rtype, {})
                    values = record.get("values", [])
                    if rtype == "a":
                        dns_data["a"] = [v.get("ip") for v in values if v.get("ip")]
                    elif rtype == "aaaa":
                        dns_data["aaaa"] = [v.get("ipv6") for v in values if v.get("ipv6")]
                    elif rtype == "mx":
                        dns_data["mx"] = [
                            {"priority": v.get("priority"), "host": v.get("host")}
                            for v in values
                        ]
                    elif rtype == "ns":
                        dns_data["ns"] = [v.get("nameserver") for v in values if v.get("nameserver")]
                    elif rtype == "txt":
                        dns_data["txt"] = [v.get("value") for v in values if v.get("value")]

                return [
                    IntelResult(
                        source=self.name,
                        source_type=self.source_type,
                        data={
                            "domain": selector.value,
                            "hostname": body.get("hostname"),
                            "alexa_rank": body.get("alexa_rank"),
                            "apex_domain": body.get("apex_domain"),
                            "dns": dns_data,
                            "subdomain_count": body.get("subdomain_count", 0),
                        },
                        confidence=0.9,
                        raw=body,
                    )
                ]
        except Exception:
            return []
