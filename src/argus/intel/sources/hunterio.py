"""Hunter.io email finder and verifier source."""

from __future__ import annotations

from argus.intel.base import BaseIntelSource
from argus.models.intel import IntelResult, IntelSelector, SelectorType

_SUPPORTED = {SelectorType.EMAIL, SelectorType.DOMAIN}


class HunterIOSource(BaseIntelSource):
    name = "hunter"
    source_type = "identity"
    requires_api_key = True
    rate_limit_per_minute = 15

    async def query(self, selector: IntelSelector) -> list[IntelResult]:
        if selector.selector_type not in _SUPPORTED:
            return []

        api_key = self._get_api_key()
        if not api_key:
            return []

        try:
            if selector.selector_type == SelectorType.DOMAIN:
                return await self._domain_search(selector.value, api_key)
            return await self._email_verify(selector.value, api_key)
        except Exception:
            return []

    async def _domain_search(self, domain: str, api_key: str) -> list[IntelResult]:
        url = "https://api.hunter.io/v2/domain-search"
        params = {"domain": domain, "api_key": api_key}

        async with self.session.get(url, params=params) as resp:
            if resp.status != 200:
                return []
            body = await resp.json()
            data_block = body.get("data", {})
            emails = data_block.get("emails", [])
            return [
                IntelResult(
                    source=self.name,
                    source_type=self.source_type,
                    data={
                        "domain": domain,
                        "organization": data_block.get("organization"),
                        "email_count": len(emails),
                        "pattern": data_block.get("pattern"),
                        "emails": [
                            {
                                "value": e.get("value"),
                                "type": e.get("type"),
                                "confidence": e.get("confidence"),
                                "first_name": e.get("first_name"),
                                "last_name": e.get("last_name"),
                                "position": e.get("position"),
                            }
                            for e in emails[:20]
                        ],
                    },
                    confidence=0.8,
                    raw=body,
                )
            ]

    async def _email_verify(self, email: str, api_key: str) -> list[IntelResult]:
        url = "https://api.hunter.io/v2/email-verifier"
        params = {"email": email, "api_key": api_key}

        async with self.session.get(url, params=params) as resp:
            if resp.status != 200:
                return []
            body = await resp.json()
            data_block = body.get("data", {})
            return [
                IntelResult(
                    source=self.name,
                    source_type=self.source_type,
                    data={
                        "email": email,
                        "result": data_block.get("result"),
                        "score": data_block.get("score"),
                        "status": data_block.get("status"),
                        "disposable": data_block.get("disposable"),
                        "webmail": data_block.get("webmail"),
                        "mx_records": data_block.get("mx_records"),
                        "smtp_server": data_block.get("smtp_server"),
                        "smtp_check": data_block.get("smtp_check"),
                    },
                    confidence=0.85,
                    raw=body,
                )
            ]
