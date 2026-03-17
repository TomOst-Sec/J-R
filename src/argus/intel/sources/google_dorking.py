"""Google dorking — generate targeted search queries for OSINT."""

from __future__ import annotations

from argus.intel.base import BaseIntelSource
from argus.models.intel import IntelResult, IntelSelector, SelectorType


class GoogleDorkingSource(BaseIntelSource):
    """Generate Google dork queries for various selector types.

    This source does not execute searches — it produces dork strings
    that can be used manually or via a search API.
    """

    name = "google_dorking"
    source_type = "records"
    requires_api_key = False
    rate_limit_per_minute = 60

    async def query(self, selector: IntelSelector) -> list[IntelResult]:
        dorks = self._generate_dorks(selector)
        if not dorks:
            return []
        return [
            IntelResult(
                source=self.name,
                source_type=self.source_type,
                data={"dorks": dorks, "selector": selector.value},
                confidence=0.3,
            )
        ]

    @staticmethod
    def _generate_dorks(selector: IntelSelector) -> list[str]:
        value = selector.value
        st = selector.selector_type

        if st == SelectorType.NAME:
            return [
                f'site:linkedin.com/in "{value}"',
                f'site:github.com "{value}"',
                f'site:twitter.com "{value}"',
                f'site:facebook.com "{value}"',
                f'site:instagram.com "{value}"',
                f'"{value}" filetype:pdf',
                f'"{value}" resume OR cv',
                f'"{value}" site:scholar.google.com',
                f'intext:"{value}" site:medium.com',
            ]
        if st == SelectorType.EMAIL:
            return [
                f'"{value}"',
                f'"{value}" filetype:pdf',
                f'"{value}" filetype:xlsx OR filetype:csv',
                f'"{value}" site:pastebin.com',
                f'intext:"{value}" site:github.com',
                f'"{value}" site:linkedin.com',
            ]
        if st == SelectorType.USERNAME:
            return [
                f'"{value}" site:github.com',
                f'"{value}" site:reddit.com',
                f'"{value}" site:twitter.com',
                f'"{value}" site:keybase.io',
                f'"{value}" site:steamcommunity.com',
                f'inurl:"{value}" site:linktr.ee',
            ]
        if st == SelectorType.DOMAIN:
            return [
                f"site:{value}",
                f'"{value}" filetype:pdf',
                f"link:{value}",
                f'inurl:"{value}" -site:{value}',
                f'"{value}" site:github.com',
            ]
        if st == SelectorType.PHONE:
            return [
                f'"{value}"',
                f'"{value}" filetype:pdf',
                f'"{value}" site:linkedin.com',
            ]
        if st == SelectorType.IP:
            return [
                f'"{value}"',
                f'"{value}" site:shodan.io',
                f'"{value}" site:censys.io',
            ]
        return []
