from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from ..domain_types import EmailFormat


AllowedChangedDimension = Literal["messaging_angle", "email_format", "subject_variant", "language"]


class AbVariantIn(BaseModel):
    messaging_angle: str
    email_format: EmailFormat
    subject_variant: str | None = None
    language: str | None = "en"


class AbTestCreate(BaseModel):
    name: str
    segment: str
    country: str
    max_emails_total: int = Field(ge=1)
    active: bool = True
    comparison_mode: str
    changed_dimensions: list[AllowedChangedDimension]
    variant_a: AbVariantIn
    variant_b: AbVariantIn

    @model_validator(mode="after")
    def validate_variants(self) -> "AbTestCreate":
        changed: list[str] = []
        for field_name in ("messaging_angle", "email_format", "subject_variant", "language"):
            if getattr(self.variant_a, field_name) != getattr(self.variant_b, field_name):
                changed.append(field_name)
        if not changed:
            raise ValueError("variant_a and variant_b must differ on at least one field")

        if set(changed) != set(self.changed_dimensions):
            raise ValueError("changed_dimensions must match actual differences between A and B")
        return self

    @property
    def max_emails_a(self) -> int:
        return int(math.ceil(self.max_emails_total / 2))

    @property
    def max_emails_b(self) -> int:
        return int(math.floor(self.max_emails_total / 2))


class AbVariantOut(BaseModel):
    variant_id: int
    ab_test_id: int
    side: Literal["A", "B"]
    messaging_angle: str
    email_format: EmailFormat
    subject_variant: str | None = None
    language: str | None = "en"
    created_at: str


class AbTestOut(BaseModel):
    ab_test_id: int
    name: str
    segment: str
    country: str
    comparison_mode: str
    changed_dimensions: list[AllowedChangedDimension]
    max_emails_total: int
    max_emails_a: int
    max_emails_b: int
    winner_metric: str
    created_at: str
    active: int
    written_a: int = 0
    written_b: int = 0
    sent_a: int = 0
    sent_b: int = 0


class AbResultsOut(BaseModel):
    ab_test_id: int
    written_a: int
    written_b: int
    sent_a: int
    sent_b: int
    opened_a: int
    opened_b: int
    replied_a: int
    replied_b: int
    reply_rate_a: float
    reply_rate_b: float
    winner_side: Literal["A", "B", "tie", "insufficient_data"]
