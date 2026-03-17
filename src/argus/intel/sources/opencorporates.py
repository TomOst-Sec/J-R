"""OpenCorporates — corporate officer/company search."""

from __future__ import annotations

from argus.intel.base import BaseIntelSource
from argus.models.intel import IntelResult, IntelSelector, SelectorType

_API_BASE = "https://api.opencorporates.com/v0.4"


class OpenCorporatesSource(BaseIntelSource):
    """Search OpenCorporates for corporate officer and company records."""

    name = "opencorporates"
    source_type = "records"
    requires_api_key = False
    rate_limit_per_minute = 10

    async def query(self, selector: IntelSelector) -> list[IntelResult]:
        if selector.selector_type != SelectorType.NAME:
            return []
        results = []
        # Search officers
        try:
            async with self.session.get(
                f"{_API_BASE}/officers/search",
                params={"q": selector.value, "per_page": "10"},
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    officers = data.get("results", {}).get("officers", [])
                    for officer in officers:
                        o = officer.get("officer", {})
                        results.append(
                            IntelResult(
                                source=self.name,
                                source_type=self.source_type,
                                data={
                                    "name": o.get("name"),
                                    "position": o.get("position"),
                                    "company_name": o.get("company", {}).get("name"),
                                    "company_number": o.get("company", {}).get("company_number"),
                                    "jurisdiction": o.get("company", {}).get("jurisdiction_code"),
                                    "start_date": o.get("start_date"),
                                    "end_date": o.get("end_date"),
                                    "opencorporates_url": o.get("opencorporates_url"),
                                },
                                confidence=0.6,
                            )
                        )
        except Exception:
            pass
        # Search companies
        try:
            async with self.session.get(
                f"{_API_BASE}/companies/search",
                params={"q": selector.value, "per_page": "5"},
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    companies = data.get("results", {}).get("companies", [])
                    for company in companies:
                        c = company.get("company", {})
                        results.append(
                            IntelResult(
                                source=self.name,
                                source_type=self.source_type,
                                data={
                                    "type": "company",
                                    "name": c.get("name"),
                                    "company_number": c.get("company_number"),
                                    "jurisdiction": c.get("jurisdiction_code"),
                                    "incorporation_date": c.get("incorporation_date"),
                                    "company_type": c.get("company_type"),
                                    "current_status": c.get("current_status"),
                                    "opencorporates_url": c.get("opencorporates_url"),
                                },
                                confidence=0.5,
                            )
                        )
        except Exception:
            pass
        return results
