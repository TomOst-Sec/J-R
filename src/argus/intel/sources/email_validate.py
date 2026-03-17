"""Email validation source via MX record check."""

from __future__ import annotations

from argus.intel.base import BaseIntelSource
from argus.models.intel import IntelResult, IntelSelector, SelectorType


class EmailValidateSource(BaseIntelSource):
    name = "email_validate"
    source_type = "identity"
    requires_api_key = False
    rate_limit_per_minute = 30

    async def query(self, selector: IntelSelector) -> list[IntelResult]:
        if selector.selector_type != SelectorType.EMAIL:
            return []

        email = selector.value
        if "@" not in email:
            return [
                IntelResult(
                    source=self.name,
                    source_type=self.source_type,
                    data={"email": email, "valid_format": False, "has_mx": False},
                    confidence=1.0,
                )
            ]

        _, domain = email.rsplit("@", 1)

        try:
            # Check MX records via Google DNS
            url = "https://dns.google/resolve"
            params = {"name": domain, "type": "MX"}
            async with self.session.get(url, params=params) as resp:
                if resp.status != 200:
                    return []
                body = await resp.json()
                answers = body.get("Answer", [])
                mx_records = [a.get("data", "") for a in answers]
                has_mx = len(mx_records) > 0

                return [
                    IntelResult(
                        source=self.name,
                        source_type=self.source_type,
                        data={
                            "email": email,
                            "domain": domain,
                            "valid_format": True,
                            "has_mx": has_mx,
                            "mx_records": mx_records,
                        },
                        confidence=0.9 if has_mx else 0.7,
                    )
                ]
        except Exception:
            return []
