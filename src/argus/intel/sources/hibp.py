"""Have I Been Pwned breach lookup source."""

from __future__ import annotations

from argus.intel.base import BaseIntelSource
from argus.models.intel import IntelResult, IntelSelector, SelectorType


class HIBPSource(BaseIntelSource):
    name = "hibp"
    source_type = "breach"
    requires_api_key = True
    rate_limit_per_minute = 10

    async def query(self, selector: IntelSelector) -> list[IntelResult]:
        if selector.selector_type != SelectorType.EMAIL:
            return []

        api_key = self._get_api_key()
        if not api_key:
            return []

        url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{selector.value}"
        headers = {
            "hibp-api-key": api_key,
            "User-Agent": "Argus-OSINT",
        }

        try:
            async with self.session.get(url, headers=headers) as resp:
                if resp.status == 404:
                    return [
                        IntelResult(
                            source=self.name,
                            source_type=self.source_type,
                            data={"email": selector.value, "breaches": [], "found": False},
                            confidence=1.0,
                        )
                    ]
                if resp.status != 200:
                    return []
                breaches = await resp.json()
                return [
                    IntelResult(
                        source=self.name,
                        source_type=self.source_type,
                        data={
                            "email": selector.value,
                            "found": True,
                            "breach_count": len(breaches),
                            "breaches": [
                                {
                                    "name": b.get("Name"),
                                    "domain": b.get("Domain"),
                                    "date": b.get("BreachDate"),
                                    "data_classes": b.get("DataClasses", []),
                                    "is_verified": b.get("IsVerified", False),
                                    "description": b.get("Description"),
                                }
                                for b in breaches
                            ],
                        },
                        confidence=0.95,
                        raw={"breaches": breaches},
                    )
                ]
        except Exception:
            return []
