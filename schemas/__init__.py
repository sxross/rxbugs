"""Pydantic schemas for request/response validation."""

from .bugs import BugCreate, BugUpdate, CloseRequest

__all__ = ["BugCreate", "BugUpdate", "CloseRequest"]
