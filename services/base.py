"""Base service class with shared transaction utilities."""

from __future__ import annotations

from sqlalchemy import Engine


class BaseService:
    """Base class for all services.
    
    Provides shared utilities for transaction management and engine access.
    """
    
    def __init__(self, engine: Engine):
        self._engine = engine
