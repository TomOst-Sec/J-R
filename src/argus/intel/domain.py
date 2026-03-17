"""Domain intelligence -- WHOIS, DNS, certificate transparency, Wayback Machine."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from argus.intel.base import BaseIntelSource, IntelSourceRegistry
from argus.models.intel import (
    CertRecord,
    DNSRecordSet,
    DomainReport,
    IntelResult,
    IntelSelector,
    SelectorType,
    WhoisRecord,
)

if TYPE_CHECKING:
    import aiohttp

    from argus.config.settings import ArgusConfig

logger = logging.getLogger(__name__)


class DomainIntelModule:
    """Aggregate domain intelligence from multiple sources."""

    def __init__(self, session: aiohttp.ClientSession, config: ArgusConfig) -> None:
        self.session = session
        self.config = config
        self._registry = IntelSourceRegistry()
        self._registry.discover_sources()

    async def investigate(self, domain: str) -> DomainReport:
        """Run whois, dns, crtsh, wayback sources in parallel and aggregate."""
        selector = IntelSelector(selector_type=SelectorType.DOMAIN, value=domain)

        # Instantiate available sources
        source_names = ["whois", "dns", "crtsh", "wayback"]
        sources: list[BaseIntelSource] = []
        for name in source_names:
            src_cls = self._registry.get_source(name)
            if src_cls is not None:
                src = src_cls(self.session, self.config)
                if await src.is_available():
                    sources.append(src)

        # Run source queries in parallel
        tasks = [src.query(selector) for src in sources]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        report = DomainReport(domain=domain)
        all_intel: list[IntelResult] = []

        for i, result in enumerate(raw_results):
            if isinstance(result, Exception):
                logger.warning("Source query failed: %s", result)
                continue
            if not isinstance(result, list):
                continue
            for ir in result:
                all_intel.append(ir)
                self._merge_intel(report, ir)

        report.sources = all_intel
        return report

    def _merge_intel(self, report: DomainReport, ir: IntelResult) -> None:
        """Merge an IntelResult into the DomainReport."""
        if ir.source == "whois":
            data = ir.data
            report.whois = WhoisRecord(
                domain=report.domain,
                registrant=data.get("registrant"),
                registrant_org=data.get("registrant_org"),
                registrant_email=data.get("registrant_email"),
                creation_date=data.get("creation_date"),
                expiry_date=data.get("expiry_date"),
                updated_date=data.get("updated_date"),
                nameservers=data.get("nameservers", []),
                registrar=data.get("registrar"),
                status=data.get("status", []),
                raw=ir.raw,
            )
        elif ir.source == "dns":
            data = ir.data
            report.dns = DNSRecordSet(
                domain=report.domain,
                a=data.get("a", []),
                aaaa=data.get("aaaa", []),
                mx=data.get("mx", []),
                txt=data.get("txt", []),
                ns=data.get("ns", []),
                cname=data.get("cname", []),
                soa=data.get("soa"),
            )
        elif ir.source == "crtsh":
            for cert_data in ir.data.get("certificates", []):
                report.certificates.append(
                    CertRecord(
                        domain=report.domain,
                        issuer=cert_data.get("issuer"),
                        common_name=cert_data.get("common_name"),
                        not_before=cert_data.get("not_before"),
                        not_after=cert_data.get("not_after"),
                        san_list=cert_data.get("san_list", []),
                    )
                )
            report.subdomains.extend(ir.data.get("subdomains", []))
        elif ir.source == "wayback":
            report.wayback_snapshots = ir.data.get("snapshot_count")
            report.wayback_first_seen = ir.data.get("first_seen")
            report.wayback_last_seen = ir.data.get("last_seen")
