"""Wayback Machine historical snapshot source."""

from __future__ import annotations

from argus.intel.base import BaseIntelSource
from argus.models.intel import IntelResult, IntelSelector, SelectorType


class WaybackSource(BaseIntelSource):
    name = "wayback"
    source_type = "network"
    requires_api_key = False
    rate_limit_per_minute = 15

    async def query(self, selector: IntelSelector) -> list[IntelResult]:
        if selector.selector_type != SelectorType.DOMAIN:
            return []

        domain = selector.value
        data: dict = {"domain": domain}

        try:
            # CDX API for snapshot listing
            cdx_url = "https://web.archive.org/cdx/search/cdx"
            cdx_params = {
                "url": domain,
                "output": "json",
                "limit": "10",
                "fl": "timestamp,statuscode,original",
            }
            async with self.session.get(cdx_url, params=cdx_params) as resp:
                if resp.status == 200:
                    rows = await resp.json()
                    # First row is header
                    if rows and len(rows) > 1:
                        header = rows[0]
                        snapshots = [dict(zip(header, row)) for row in rows[1:]]
                        data["snapshots"] = snapshots
                        data["snapshot_count"] = len(snapshots)
                        if snapshots:
                            data["first_seen"] = snapshots[0].get("timestamp")
                            data["last_seen"] = snapshots[-1].get("timestamp")

            # Availability API
            avail_url = "https://archive.org/wayback/available"
            avail_params = {"url": domain}
            async with self.session.get(avail_url, params=avail_params) as resp:
                if resp.status == 200:
                    body = await resp.json()
                    closest = body.get("archived_snapshots", {}).get("closest", {})
                    if closest:
                        data["latest_snapshot"] = {
                            "url": closest.get("url"),
                            "timestamp": closest.get("timestamp"),
                            "status": closest.get("status"),
                            "available": closest.get("available", False),
                        }

            return [
                IntelResult(
                    source=self.name,
                    source_type=self.source_type,
                    data=data,
                    confidence=0.85 if data.get("snapshots") else 0.3,
                )
            ]
        except Exception:
            return []
