"""Bug service layer for orchestrating bug operations."""

from __future__ import annotations

from typing import Any, TypedDict

from sqlalchemy import Engine

import db.annotations as annotations_repo
import db.bugs as bugs_repo
import db.relations as relations_repo
from .base import BaseService


class CloseBugResult(TypedDict):
    """Result of closing a bug with optional warnings."""
    bug: dict[str, Any]
    warnings: list[str]


class BugService(BaseService):
    """Service for bug-related business logic.
    
    Orchestrates multi-step operations within transactions and enforces
    business rules (e.g., warnings for duplicate/fixed resolutions).
    """
    
    def close_bug_with_annotation(
        self,
        bug_id: str,
        resolution: str,
        annotation_body: str | None,
        actor: str,
        actor_type: str,
    ) -> CloseBugResult:
        """Close a bug with an optional annotation in a single transaction.
        
        Args:
            bug_id: The bug identifier
            resolution: Resolution type (e.g., "fixed", "duplicate", "wontfix")
            annotation_body: Optional annotation text to add
            actor: Actor performing the close (human username or agent name)
            actor_type: Type of actor ("human" or "agent")
            
        Returns:
            Dictionary with "bug" (updated bug dict) and "warnings" (list of strings)
            
        Raises:
            ValueError: If bug is already closed or resolution is invalid
        """
        # Compute warnings before starting transaction (read-only queries)
        warnings = self._compute_close_warnings(bug_id, resolution, annotation_body)
        
        # Execute both operations in a single transaction
        with self._engine.begin() as conn:
            # Close the bug
            bug = bugs_repo.close(
                self._engine,
                bug_id,
                resolution=resolution,
                actor=actor,
                actor_type=actor_type,
            )
            
            # Add annotation if provided
            if annotation_body:
                annotations_repo.create(
                    self._engine,
                    bug_id=bug_id,
                    author=actor,
                    author_type=actor_type,
                    body=annotation_body,
                )
        
        # Return bug with warnings only if there are any
        result: CloseBugResult = {"bug": bug, "warnings": warnings}
        if not warnings:
            del result["warnings"]
        return result
    
    def _compute_close_warnings(
        self,
        bug_id: str,
        resolution: str,
        annotation_body: str | None,
    ) -> list[str]:
        """Compute warnings for closing a bug.
        
        Args:
            bug_id: The bug identifier
            resolution: Resolution type
            annotation_body: Optional annotation text
            
        Returns:
            List of warning messages
        """
        warnings = []
        
        # Warn if closing as duplicate without linking to canonical bug
        if resolution == "duplicate":
            related = relations_repo.list_for_bug(self._engine, bug_id)
            if not related:
                warnings.append(
                    "Closing as 'duplicate' without linking the canonical bug is not recommended."
                )
        
        # Warn if closing as fixed without any annotation
        if resolution == "fixed":
            existing = annotations_repo.list_for_bug(self._engine, bug_id)
            if not existing and not annotation_body:
                warnings.append(
                    "Closing as 'fixed' without an annotation is not recommended."
                )
        
        return warnings
