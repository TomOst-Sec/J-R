"""PGP key server lookup source."""

from __future__ import annotations

from argus.intel.base import BaseIntelSource
from argus.models.intel import IntelResult, IntelSelector, SelectorType


class PGPSource(BaseIntelSource):
    name = "pgp"
    source_type = "identity"
    requires_api_key = False
    rate_limit_per_minute = 20

    async def query(self, selector: IntelSelector) -> list[IntelResult]:
        if selector.selector_type != SelectorType.EMAIL:
            return []

        email = selector.value
        results: list[dict] = []

        try:
            # OpenPGP key server (VKS)
            vks_url = f"https://keys.openpgp.org/vks/v1/by-email/{email}"
            async with self.session.get(vks_url) as resp:
                if resp.status == 200:
                    key_data = await resp.text()
                    results.append({
                        "server": "keys.openpgp.org",
                        "found": True,
                        "key_material": key_data[:500] if key_data else None,
                    })
        except Exception:
            pass

        try:
            # Ubuntu key server (HKP)
            hkp_url = "https://keyserver.ubuntu.com/pks/lookup"
            hkp_params = {"search": email, "op": "index", "options": "mr"}
            async with self.session.get(hkp_url, params=hkp_params) as resp:
                if resp.status == 200:
                    body = await resp.text()
                    # Parse machine-readable output
                    keys = []
                    for line in body.splitlines():
                        parts = line.split(":")
                        if parts and parts[0] == "pub":
                            keys.append({
                                "key_id": parts[1] if len(parts) > 1 else None,
                                "algorithm": parts[2] if len(parts) > 2 else None,
                                "key_length": parts[3] if len(parts) > 3 else None,
                                "creation_date": parts[4] if len(parts) > 4 else None,
                            })
                    if keys:
                        results.append({
                            "server": "keyserver.ubuntu.com",
                            "found": True,
                            "keys": keys,
                        })
        except Exception:
            pass

        if not results:
            return []

        return [
            IntelResult(
                source=self.name,
                source_type=self.source_type,
                data={
                    "email": email,
                    "pgp_found": True,
                    "servers": results,
                },
                confidence=0.85,
            )
        ]
