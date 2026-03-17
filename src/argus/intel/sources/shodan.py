"""Shodan network intelligence source."""

from __future__ import annotations

from argus.intel.base import BaseIntelSource
from argus.models.intel import IntelResult, IntelSelector, SelectorType

_SUPPORTED = {SelectorType.IP, SelectorType.DOMAIN}


class ShodanSource(BaseIntelSource):
    name = "shodan"
    source_type = "network"
    requires_api_key = True
    rate_limit_per_minute = 10

    async def query(self, selector: IntelSelector) -> list[IntelResult]:
        if selector.selector_type not in _SUPPORTED:
            return []

        api_key = self._get_api_key()
        if not api_key:
            return []

        try:
            if selector.selector_type == SelectorType.DOMAIN:
                return await self._query_domain(selector.value, api_key)
            return await self._query_ip(selector.value, api_key)
        except Exception:
            return []

    async def _query_domain(self, domain: str, api_key: str) -> list[IntelResult]:
        # Resolve domain to IP first
        url = "https://api.shodan.io/dns/resolve"
        params = {"hostnames": domain, "key": api_key}

        async with self.session.get(url, params=params) as resp:
            if resp.status != 200:
                return []
            body = await resp.json()
            ip = body.get(domain)
            if not ip:
                return []

        results = await self._query_ip(ip, api_key)
        for r in results:
            r.data["resolved_from_domain"] = domain
        return results

    async def _query_ip(self, ip: str, api_key: str) -> list[IntelResult]:
        url = f"https://api.shodan.io/shodan/host/{ip}"
        params = {"key": api_key}

        async with self.session.get(url, params=params) as resp:
            if resp.status != 200:
                return []
            body = await resp.json()
            return [
                IntelResult(
                    source=self.name,
                    source_type=self.source_type,
                    data={
                        "ip": ip,
                        "hostnames": body.get("hostnames", []),
                        "os": body.get("os"),
                        "ports": body.get("ports", []),
                        "org": body.get("org"),
                        "isp": body.get("isp"),
                        "country": body.get("country_name"),
                        "city": body.get("city"),
                        "vulns": body.get("vulns", []),
                        "services": [
                            {
                                "port": s.get("port"),
                                "transport": s.get("transport"),
                                "product": s.get("product"),
                                "version": s.get("version"),
                            }
                            for s in body.get("data", [])[:20]
                        ],
                    },
                    confidence=0.9,
                    raw=body,
                )
            ]
