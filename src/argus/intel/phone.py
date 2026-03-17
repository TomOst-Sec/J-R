"""Phone intelligence -- number validation, carrier lookup, geolocation."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from argus.intel.base import IntelSourceRegistry
from argus.models.intel import IntelResult, IntelSelector, PhoneMetadata, SelectorType

if TYPE_CHECKING:
    import aiohttp

    from argus.config.settings import ArgusConfig

logger = logging.getLogger(__name__)


class PhoneIntelModule:
    """Phone number intelligence gathering."""

    def __init__(self, session: aiohttp.ClientSession, config: ArgusConfig) -> None:
        self.session = session
        self.config = config
        self._registry = IntelSourceRegistry()
        self._registry.discover_sources()

    async def investigate(self, phone: str) -> tuple[PhoneMetadata, list[IntelResult]]:
        """Validate and investigate a phone number.

        Returns a tuple of (PhoneMetadata, list of IntelResult from sources).
        """
        metadata = self._parse_phone(phone)

        # Query any registered phone_lookup sources
        selector = IntelSelector(selector_type=SelectorType.PHONE, value=phone)
        src_cls = self._registry.get_source("phone_lookup")
        intel_results: list[IntelResult] = []

        if src_cls is not None:
            src = src_cls(self.session, self.config)
            if await src.is_available():
                try:
                    intel_results = await src.query(selector)
                except Exception:
                    logger.warning("phone_lookup source query failed")

        return metadata, intel_results

    @staticmethod
    def _parse_phone(phone: str) -> PhoneMetadata:
        """Parse a phone number using the phonenumbers library."""
        try:
            import phonenumbers
            from phonenumbers import carrier as pn_carrier
            from phonenumbers import geocoder as pn_geocoder
            from phonenumbers import number_type as pn_number_type

            parsed = phonenumbers.parse(phone, None)
            is_valid = phonenumbers.is_valid_number(parsed)
            is_possible = phonenumbers.is_possible_number(parsed)

            country_code = str(parsed.country_code)
            region = phonenumbers.region_code_for_number(parsed)
            carrier_name = pn_carrier.name_for_number(parsed, "en")
            geo_desc = pn_geocoder.description_for_number(parsed, "en")

            # Map number type
            nt = pn_number_type(parsed)
            type_map = {
                phonenumbers.PhoneNumberType.MOBILE: "mobile",
                phonenumbers.PhoneNumberType.FIXED_LINE: "fixed_line",
                phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE: "fixed_line_or_mobile",
                phonenumbers.PhoneNumberType.VOIP: "voip",
                phonenumbers.PhoneNumberType.TOLL_FREE: "toll_free",
                phonenumbers.PhoneNumberType.PREMIUM_RATE: "premium_rate",
            }
            line_type = type_map.get(nt, "unknown")

            return PhoneMetadata(
                number=phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164),
                country_code=country_code,
                country=geo_desc or None,
                carrier=carrier_name or None,
                line_type=line_type,
                is_valid=is_valid,
                is_possible=is_possible,
                region=region,
            )
        except ImportError:
            logger.warning("phonenumbers library not installed -- returning basic metadata")
            return PhoneMetadata(number=phone, is_valid=False, is_possible=False)
        except Exception as exc:
            logger.warning("Phone parsing failed: %s", exc)
            return PhoneMetadata(number=phone, is_valid=False, is_possible=False)
