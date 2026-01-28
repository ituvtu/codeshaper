from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class FocusEnum(str, Enum):
    security = "security"
    performance = "performance"
    clean_code = "clean_code"


class SeverityEnum(str, Enum):
    info = "info"
    warning = "warning"
    error = "error"


class Issue(BaseModel):
    severity: SeverityEnum
    line: int = Field(..., ge=1)
    description: str


class ReviewRequest(BaseModel):
    code: str = Field(..., min_length=1)
    language: str = Field(..., min_length=1)
    focus: FocusEnum | None = Field(None)


class ReviewResponse(BaseModel):
    summary: str
    rating: int = Field(..., ge=1, le=10)
    issues: list[Issue]
    refactored_code: str | None = None


class RefactorRequest(BaseModel):
    code: str = Field(..., min_length=1)
    language: str = Field(..., min_length=1)
    issues: list[str] | None = Field(None, description="List of issues to fix")


class RefactorResponse(BaseModel):
    refactored_code: str
    changes_made: list[str] | None = Field(None, description="List of changes applied")


class ReviewAndRefactorResponse(BaseModel):
    """Combined response with both review and refactored code."""
    summary: str
    rating: int = Field(..., ge=1, le=10)
    issues: list[Issue]
    refactored_code: str
    changes_made: list[str] | None = None


class HealthResponse(BaseModel):
    status: Literal["ok"]
