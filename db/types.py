"""Shared type definitions for the repository layer.

All repository functions accept and return objects defined here,
never raw SQLAlchemy rows.  Routes depend only on these types.
"""

from __future__ import annotations

from typing import Literal, Optional, TypedDict

# ---------------------------------------------------------------------------
# Enum types
# ---------------------------------------------------------------------------

Area = Literal["ui", "middleware", "backend", "database", "sync"]
Priority = Literal[1, 2, 3]
Severity = Literal["showstopper", "serious", "enhancement", "nice_to_have"]
Status = Literal["open", "closed"]
Resolution = Literal["none", "fixed", "no_repro", "duplicate", "wont_fix"]
ActorType = Literal["human", "agent"]

# ---------------------------------------------------------------------------
# Bugs
# ---------------------------------------------------------------------------


class Bug(TypedDict):
    id: str
    product: str
    title: str
    description: str | None
    area: Area | None
    priority: Priority | None
    severity: Severity | None
    status: Status
    resolution: Resolution
    created_at: str
    updated_at: str


class BugSummary(TypedDict):
    """Lightweight version returned by search / list."""

    id: str
    product: str
    title: str
    area: Area | None
    priority: Priority | None
    severity: Severity | None
    status: Status
    resolution: Resolution
    created_at: str
    updated_at: str


class BugFilters(TypedDict, total=False):
    q: str
    product: list[str]
    area: list[Area]
    priority: list[Priority]
    severity: list[Severity]
    status: Status
    resolution: list[Resolution]
    related_to: str
    has_artifacts: bool
    created_after: str
    created_before: str


# ---------------------------------------------------------------------------
# Annotations
# ---------------------------------------------------------------------------


class Annotation(TypedDict):
    id: int
    bug_id: str
    author: str
    author_type: ActorType
    body: str
    created_at: str


# ---------------------------------------------------------------------------
# Artifacts
# ---------------------------------------------------------------------------


class Artifact(TypedDict):
    id: int
    bug_id: str
    filename: str
    path: str
    mime_type: str | None
    uploaded_at: str


# ---------------------------------------------------------------------------
# Relations
# ---------------------------------------------------------------------------


class Relation(TypedDict):
    bug_id: str
    related_id: str


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------


class Product(TypedDict):
    name: str
    description: str | None
    archived: bool
    bug_count: int


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------


class Agent(TypedDict):
    key: str
    name: str
    description: str | None
    created_at: str
    active: bool


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------


class AuditEntry(TypedDict):
    id: int
    bug_id: str
    actor: str
    actor_type: ActorType
    field: str
    old_value: str | None
    new_value: str | None
    changed_at: str
