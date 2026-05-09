"""Service layer for RxBugs.

Services orchestrate business logic and coordinate between repositories,
ensuring operations are performed within proper transaction boundaries.
"""

from .bugs import BugService

__all__ = ["BugService"]
