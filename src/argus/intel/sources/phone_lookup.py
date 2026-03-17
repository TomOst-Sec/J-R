"""Phone number metadata lookup source."""

from __future__ import annotations

from argus.intel.base import BaseIntelSource
from argus.models.intel import IntelResult, IntelSelector, SelectorType

try:
    import phonenumbers
    from phonenumbers import carrier as pn_carrier
    from phonenumbers import geocoder as pn_geocoder
    from phonenumbers import timezone as pn_timezone

    _HAS_PHONENUMBERS = True
except ImportError:
    _HAS_PHONENUMBERS = False


class PhoneLookupSource(BaseIntelSource):
    name = "phone_lookup"
    source_type = "identity"
    requires_api_key = False
    rate_limit_per_minute = 60

    async def is_available(self) -> bool:
        return _HAS_PHONENUMBERS

    async def query(self, selector: IntelSelector) -> list[IntelResult]:
        if selector.selector_type != SelectorType.PHONE:
            return []
        if not _HAS_PHONENUMBERS:
            return []

        try:
            parsed = phonenumbers.parse(selector.value, None)
            is_valid = phonenumbers.is_valid_number(parsed)
            is_possible = phonenumbers.is_possible_number(parsed)

            carrier_name = ""
            try:
                carrier_name = pn_carrier.name_for_number(parsed, "en")
            except Exception:
                pass

            region = phonenumbers.region_code_for_number(parsed)
            country = ""
            try:
                country = pn_geocoder.description_for_number(parsed, "en")
            except Exception:
                pass

            timezones = []
            try:
                timezones = list(pn_timezone.time_zones_for_number(parsed))
            except Exception:
                pass

            return [
                IntelResult(
                    source=self.name,
                    source_type=self.source_type,
                    data={
                        "number": selector.value,
                        "formatted": phonenumbers.format_number(
                            parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL
                        ),
                        "country_code": str(parsed.country_code),
                        "country": country,
                        "region": region,
                        "carrier": carrier_name,
                        "is_valid": is_valid,
                        "is_possible": is_possible,
                        "number_type": str(phonenumbers.number_type(parsed)),
                        "timezones": timezones,
                    },
                    confidence=0.95 if is_valid else 0.4,
                )
            ]
        except Exception:
            return []
