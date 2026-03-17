"""OCCRP Aleph — investigative journalism entity search."""

from __future__ import annotations

from argus.intel.base import BaseIntelSource
from argus.models.intel import IntelResult, IntelSelector, SelectorType

_API_BASE = "https://aleph.occrp.org/api/2"


class AlephSource(BaseIntelSource):
    """Search OCCRP Aleph for entities related to investigations."""

    name = "aleph"
    source_type = "records"
    requires_api_key = False
    rate_limit_per_minute = 10

    async def query(self, selector: IntelSelector) -> list[IntelResult]:
        if selector.selector_type != SelectorType.NAME:
            return []
        try:
            async with self.session.get(
                f"{_API_BASE}/entities",
                params={"q": selector.value, "limit": "10"},
                headers={"Accept": "application/json"},
            ) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                results = []
                for entity in data.get("results", []):
                    properties = entity.get("properties", {})
                    results.append(
                        IntelResult(
                            source=self.name,
                            source_type=self.source_type,
                            data={
                                "entity_id": entity.get("id"),
                                "schema": entity.get("schema"),
                                "name": properties.get("name", [None])[0]
                                if isinstance(properties.get("name"), list)
                                else properties.get("name"),
                                "country": properties.get("country", []),
                                "collection_id": entity.get("collection_id"),
                                "aleph_url": entity.get("links", {}).get("self"),
                            },
                            confidence=0.4,
                        )
                    )
                return results
        except Exception:
            return []
