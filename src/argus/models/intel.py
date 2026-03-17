"""Intelligence data models for Argus OSINT platform."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SelectorType(str, Enum):
    """Types of intelligence selectors."""

    EMAIL = "email"
    PHONE = "phone"
    DOMAIN = "domain"
    IP = "ip"
    USERNAME = "username"
    NAME = "name"
    IMAGE_URL = "image_url"


class IntelSelector(BaseModel):
    """A selector for intelligence queries — the thing being investigated."""

    selector_type: SelectorType
    value: str


class IntelResult(BaseModel):
    """A single intelligence result from a data source."""

    source: str
    source_type: str
    data: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.5
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    raw: dict[str, Any] | None = None


class BreachRecord(BaseModel):
    """A record from a data breach."""

    breach_name: str
    breach_date: datetime | None = None
    data_types: list[str] = Field(default_factory=list)
    email: str | None = None
    description: str | None = None
    is_verified: bool = True
    domain: str | None = None


class WhoisRecord(BaseModel):
    """WHOIS lookup result for a domain."""

    domain: str
    registrant: str | None = None
    registrant_org: str | None = None
    registrant_email: str | None = None
    creation_date: datetime | None = None
    expiry_date: datetime | None = None
    updated_date: datetime | None = None
    nameservers: list[str] = Field(default_factory=list)
    registrar: str | None = None
    status: list[str] = Field(default_factory=list)
    raw: dict[str, Any] | None = None


class DNSRecordSet(BaseModel):
    """DNS records for a domain."""

    domain: str
    a: list[str] = Field(default_factory=list)
    aaaa: list[str] = Field(default_factory=list)
    mx: list[dict[str, Any]] = Field(default_factory=list)
    txt: list[str] = Field(default_factory=list)
    ns: list[str] = Field(default_factory=list)
    cname: list[str] = Field(default_factory=list)
    soa: dict[str, Any] | None = None


class CertRecord(BaseModel):
    """Certificate transparency record."""

    domain: str
    issuer: str | None = None
    common_name: str | None = None
    not_before: datetime | None = None
    not_after: datetime | None = None
    san_list: list[str] = Field(default_factory=list)
    serial_number: str | None = None
    fingerprint_sha256: str | None = None


class PhoneMetadata(BaseModel):
    """Phone number metadata."""

    number: str
    country_code: str | None = None
    country: str | None = None
    carrier: str | None = None
    line_type: str | None = None
    is_valid: bool = False
    is_possible: bool = False
    region: str | None = None


class EmailReport(BaseModel):
    """Comprehensive email investigation report."""

    email: str
    is_deliverable: bool | None = None
    breaches: list[BreachRecord] = Field(default_factory=list)
    gravatar_url: str | None = None
    gravatar_profile: dict[str, Any] | None = None
    pgp_keys: list[dict[str, Any]] = Field(default_factory=list)
    linked_accounts: list[dict[str, str]] = Field(default_factory=list)
    mx_records: list[str] = Field(default_factory=list)
    sources: list[IntelResult] = Field(default_factory=list)


class DomainReport(BaseModel):
    """Comprehensive domain investigation report."""

    domain: str
    whois: WhoisRecord | None = None
    dns: DNSRecordSet | None = None
    subdomains: list[str] = Field(default_factory=list)
    certificates: list[CertRecord] = Field(default_factory=list)
    wayback_snapshots: int | None = None
    wayback_first_seen: datetime | None = None
    wayback_last_seen: datetime | None = None
    technologies: list[str] = Field(default_factory=list)
    sources: list[IntelResult] = Field(default_factory=list)


class IdentityCluster(BaseModel):
    """A cluster of linked identity data across sources."""

    cluster_id: str
    accounts: list[dict[str, Any]] = Field(default_factory=list)
    emails: list[str] = Field(default_factory=list)
    usernames: list[str] = Field(default_factory=list)
    names: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    evidence: list[str] = Field(default_factory=list)
    timeline: list[dict[str, Any]] = Field(default_factory=list)
