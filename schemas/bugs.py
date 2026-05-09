"""Bug-related validation schemas."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class BugCreate(BaseModel):
    """Schema for creating a new bug."""
    
    product: str = Field(..., min_length=1, description="Product name")
    title: str = Field(..., min_length=1, description="Bug title")
    description: Optional[str] = None
    area: Optional[str] = None
    platform: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=5, description="Priority (1-5)")
    severity: Optional[str] = None
    
    @field_validator('product', 'title')
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip leading/trailing whitespace."""
        return v.strip() if v else v


class BugUpdate(BaseModel):
    """Schema for updating an existing bug."""
    
    title: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    area: Optional[str] = None
    platform: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=5)
    severity: Optional[str] = None
    
    @field_validator('title')
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        """Strip leading/trailing whitespace."""
        return v.strip() if v else v


class CloseRequest(BaseModel):
    """Schema for closing a bug."""
    
    resolution: str = Field(
        ...,
        description="Resolution type",
        pattern="^(fixed|duplicate|no_repro|wont_fix)$"
    )
    annotation: Optional[str] = Field(None, description="Optional closing annotation")
