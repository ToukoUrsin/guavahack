"""Typed, immutable structures for adaptive Guava coaching decisions."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Mode(StrEnum):
    """The continuous coaching mode selected for the conversation."""

    COACH = "coach"
    REHEARSAL = "rehearsal"
    SAFETY = "safety"
    ENDED = "ended"


class Operation(StrEnum):
    """The next state transition or content operation requested by the model."""

    STAY = "stay"
    COACH = "coach"
    CREATE = "create"
    REVISE = "revise"
    REPLAY = "replay"
    END = "end"
    SAFETY = "safety"


class ClarificationField(BaseModel):
    """A bounded, optional piece of information an activity may ask for."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str = Field(pattern=r"^[a-z][a-z0-9_]{0,39}$")
    question: str = Field(min_length=1, max_length=300)
    required: bool = False


ChecklistItem = Annotated[str, Field(min_length=1, max_length=600)]
KnownFact = Annotated[str, Field(max_length=500)]
Boundary = Annotated[str, Field(max_length=300)]


class ActivityDefinition(BaseModel):
    """A generated coaching activity with bounded prompts and clarification."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    objective: str = Field(
        min_length=1,
        max_length=2400,
        description=(
            "Instructions for what Guava does in the activity. In rehearsal, address "
            "Guava as the fictional counterpart, not as an instructor grading the caller."
        ),
    )
    completion_criteria: str = Field(default="", max_length=800)
    checklist: tuple[ChecklistItem, ...] = Field(default_factory=tuple, max_length=6)
    fields: tuple[ClarificationField, ...] = Field(default_factory=tuple, max_length=3)

    @model_validator(mode="after")
    def reject_duplicate_field_keys(self) -> ActivityDefinition:
        """Keep generated clarification fields addressable without ambiguity."""

        keys = [field.key for field in self.fields]
        if len(keys) != len(set(keys)):
            raise ValueError("fields must not contain duplicate keys")
        return self


class SceneDefinition(BaseModel):
    """A fictional rehearsal counterpart and the bounded scene context."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str = Field(min_length=1, max_length=120)
    situation: str = Field(
        min_length=1,
        max_length=1600,
        description=(
            "Summarize only the situation supplied by the caller. Do not invent "
            "item types, costs, deadlines, trips, or reasons they need something."
        ),
    )
    counterpart_name: str = Field(default="Alex", min_length=1, max_length=80)
    caller_role: str = Field(
        min_length=1,
        max_length=800,
        description=(
            "The human caller's role and position, in third person. For example: "
            "The caller owns the gear and lent it to the counterpart. Never address this role as you."
        ),
    )
    counterpart_role: str = Field(
        min_length=1,
        max_length=800,
        description=(
            "The role Guava plays, in third person. For example: the counterpart "
            "borrowed the caller's gear and has not returned it. Keep ownership unambiguous."
        ),
    )
    counterpart_description: str = Field(min_length=1, max_length=1200)
    behavior: str = Field(min_length=1, max_length=1200)
    caller_goal: str = Field(min_length=1, max_length=800)
    known_facts: tuple[KnownFact, ...] = Field(
        default_factory=tuple,
        max_length=12,
        description=(
            "Exact short quotes from caller messages establishing the scene facts. "
            "Do not paraphrase, invent facts, or include fictional counterpart assumptions."
        ),
    )
    boundaries: tuple[Boundary, ...] = Field(default_factory=tuple, max_length=8)


class Decision(BaseModel):
    """A structured adaptive decision; it carries data only, never executable code."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    operation: Operation
    scene: SceneDefinition | None = Field(
        default=None,
        description=(
            "For create and revise this MUST be a complete generated SceneDefinition, not null. "
            "For replay include it only when correcting the saved scene."
        ),
    )
    activity: ActivityDefinition | None = Field(
        default=None,
        description=(
            "For create and coach this MUST be a generated ActivityDefinition with a concrete "
            "objective, not null. Other operations may reuse the current activity."
        ),
    )
    guidance: str = Field(
        default="",
        max_length=2000,
        description=(
            "Optional concise instruction to Guava, not an explanation of your decision "
            "or a spoken setup announcement. Empty is fine when the activity says enough."
        ),
    )
    consent_quote: str = Field(
        default="",
        max_length=500,
        description=(
            "Exact words from latest_caller that request or agree to this practice. "
            "Copy them verbatim when consent is explicit; use empty string only when "
            "no current agreement/request exists. Never quote earlier consent."
        ),
    )

    @model_validator(mode="after")
    def validate_operation_payload(self) -> Decision:
        """Require only the payload needed by each operation."""

        if self.operation is Operation.CREATE:
            if self.scene is None or self.activity is None:
                raise ValueError("create requires both scene and activity")
        elif self.operation is Operation.REVISE:
            if self.scene is None:
                raise ValueError("revise requires scene")
        elif self.operation is Operation.COACH:
            if self.activity is None:
                raise ValueError("coach requires activity")
        elif self.operation in (Operation.STAY, Operation.END, Operation.SAFETY):
            if self.scene is not None or self.activity is not None:
                raise ValueError(f"{self.operation.value} must not carry scene or activity")
        return self
