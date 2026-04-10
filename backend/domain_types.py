from __future__ import annotations

from enum import Enum
from urllib.parse import SplitResult, urlsplit, urlunsplit


class LeadStatus(str, Enum):
    NEW = "new"
    WRITTEN = "written"
    CONTACTED = "contacted"


class DeliveryStatus(str, Enum):
    READY = "ready"
    SENT = "sent"


class EmailFormat(str, Enum):
    SHORT = "short"
    MEDIUM = "medium"


class EmailEventType(str, Enum):
    READY = "ready"
    SENT = "sent"
    OPENED = "opened"
    REPLIED = "replied"


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def normalize_email(value: str) -> str:
    return value.strip().lower()


def normalize_website(value: str) -> str:
    value = value.strip()
    parts = urlsplit(value)
    hostname = (parts.hostname or "").lower()
    netloc = hostname
    if parts.port is not None:
        netloc = f"{hostname}:{parts.port}"
    if parts.username:
        credentials = parts.username
        if parts.password:
            credentials = f"{credentials}:{parts.password}"
        netloc = f"{credentials}@{netloc}"
    normalized = SplitResult(
        scheme=parts.scheme.lower(),
        netloc=netloc,
        path=parts.path,
        query=parts.query,
        fragment=parts.fragment,
    )
    return urlunsplit(normalized)


def can_transition_lead_status(current: str, nxt: str) -> bool:
    if current == LeadStatus.NEW.value:
        return nxt in {LeadStatus.NEW.value, LeadStatus.WRITTEN.value, LeadStatus.CONTACTED.value}
    if current == LeadStatus.WRITTEN.value:
        return nxt in {LeadStatus.WRITTEN.value, LeadStatus.CONTACTED.value}
    if current == LeadStatus.CONTACTED.value:
        return nxt == LeadStatus.CONTACTED.value
    return False


def can_transition_delivery_status(current: str, nxt: str) -> bool:
    if current == DeliveryStatus.READY.value:
        return nxt in {DeliveryStatus.READY.value, DeliveryStatus.SENT.value}
    if current == DeliveryStatus.SENT.value:
        return nxt == DeliveryStatus.SENT.value
    return False
