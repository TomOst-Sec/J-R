"""WHOIS domain lookup source."""

from __future__ import annotations

from argus.intel.base import BaseIntelSource
from argus.models.intel import IntelResult, IntelSelector, SelectorType

try:
    import whois as _whois

    _HAS_WHOIS = True
except ImportError:
    _HAS_WHOIS = False


class WhoisSource(BaseIntelSource):
    name = "whois"
    source_type = "dns"
    requires_api_key = False
    rate_limit_per_minute = 15

    async def is_available(self) -> bool:
        return _HAS_WHOIS

    async def query(self, selector: IntelSelector) -> list[IntelResult]:
        if selector.selector_type != SelectorType.DOMAIN:
            return []
        if not _HAS_WHOIS:
            return []

        try:
            import asyncio

            loop = asyncio.get_running_loop()
            w = await loop.run_in_executor(None, _whois.whois, selector.value)

            def _to_str(val):
                if val is None:
                    return None
                if isinstance(val, list):
                    return str(val[0]) if val else None
                return str(val)

            def _to_list(val):
                if val is None:
                    return []
                if isinstance(val, list):
                    return [str(v) for v in val]
                return [str(val)]

            data = {
                "domain": selector.value,
                "registrant": _to_str(getattr(w, "name", None)),
                "registrant_org": _to_str(getattr(w, "org", None)),
                "registrant_email": _to_str(w.get("emails", None) if hasattr(w, "get") else getattr(w, "emails", None)),
                "creation_date": _to_str(getattr(w, "creation_date", None)),
                "expiry_date": _to_str(getattr(w, "expiration_date", None)),
                "updated_date": _to_str(getattr(w, "updated_date", None)),
                "nameservers": _to_list(getattr(w, "name_servers", None)),
                "registrar": _to_str(getattr(w, "registrar", None)),
                "status": _to_list(getattr(w, "status", None)),
            }

            return [
                IntelResult(
                    source=self.name,
                    source_type=self.source_type,
                    data=data,
                    confidence=0.9,
                    raw=dict(w) if hasattr(w, "__iter__") else None,
                )
            ]
        except Exception:
            return []
