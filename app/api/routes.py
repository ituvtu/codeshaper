from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api.dependencies import get_reviewer
from app.core.exceptions import UpstreamServiceError, UpstreamTimeoutError
from app.schemas.review import (
    FocusEnum,
    HealthResponse,
    RefactorRequest,
    RefactorResponse,
    ReviewAndRefactorResponse,
    ReviewRequest,
    ReviewResponse,
)
from app.services.reviewer import Reviewer

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(reviewer: Reviewer = Depends(get_reviewer)) -> HealthResponse:
    try:
        await reviewer.ping()
    except UpstreamTimeoutError as exc:  # pragma: no cover - guard path
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(exc)) from exc
    except UpstreamServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return HealthResponse(status="ok")


LANG_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".java": "java",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".c": "c",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
}


@router.post("/api/v1/review", response_model=ReviewResponse)
async def review_code(
    file: UploadFile = File(..., description="Code file to review (.py, .js, etc.)"),
    language: str | None = Form(None, description="Programming language (python, javascript, etc.)"),
    focus: str | None = Form(None, description="Review focus area"),
    reviewer: Reviewer = Depends(get_reviewer),
) -> ReviewResponse:
    try:
        content = await file.read()
        code = content.decode("utf-8")

        # language: prefer explicit form field, else infer from filename extension
        lang_value = (language or "").strip().lower()
        if not lang_value:
            ext = (file.filename or "").lower().rpartition(".")[2]
            ext = f".{ext}" if ext else ""
            lang_value = LANG_MAP.get(ext, "")
        if not lang_value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Language is required (set language field or use a known file extension)",
            )

        focus_enum: FocusEnum | None
        if focus in (None, ""):
            focus_enum = None
        else:
            try:
                focus_enum = FocusEnum(focus)
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid focus. Use security, performance, or clean_code.",
                ) from exc

        request = ReviewRequest(code=code, language=lang_value, focus=focus_enum)
        return await reviewer.review_code(request)
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be UTF-8 encoded",
        ) from exc
    except UpstreamTimeoutError as exc:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(exc)) from exc
    except UpstreamServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/api/v1/refactor", response_model=RefactorResponse)
async def refactor_code(
    request: RefactorRequest,
    reviewer: Reviewer = Depends(get_reviewer),
) -> RefactorResponse:
    """Generate refactored code, optionally based on specific issues."""
    try:
        result = await reviewer.refactor_code(
            code=request.code,
            language=request.language,
            issues=request.issues
        )
        
        return RefactorResponse(
            refactored_code=result.get("fixed_code", "// Refactoring failed"),
            changes_made=result.get("changes", [])
        )
    except UpstreamTimeoutError as exc:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(exc)) from exc
    except UpstreamServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/api/v1/review-and-refactor", response_model=ReviewAndRefactorResponse)
async def review_and_refactor_code(
    file: UploadFile = File(..., description="Code file to review and refactor"),
    language: str | None = Form(None, description="Programming language"),
    focus: str | None = Form(None, description="Review focus area"),
    reviewer: Reviewer = Depends(get_reviewer),
) -> ReviewAndRefactorResponse:
    """Combined endpoint: first reviews code, then generates refactored version based on found issues."""
    try:
        content = await file.read()
        code = content.decode("utf-8")

        # Determine language
        lang_value = (language or "").strip().lower()
        if not lang_value:
            ext = (file.filename or "").lower().rpartition(".")[2]
            ext = f".{ext}" if ext else ""
            lang_value = LANG_MAP.get(ext, "")
        if not lang_value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Language is required",
            )

        # Parse focus
        focus_enum: FocusEnum | None
        if focus in (None, ""):
            focus_enum = None
        else:
            try:
                focus_enum = FocusEnum(focus)
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid focus. Use security, performance, or clean_code.",
                ) from exc

        # Step 1: Review code
        request = ReviewRequest(code=code, language=lang_value, focus=focus_enum)
        review_result = await reviewer.review_code(request)
        
        # Step 2: Refactor based on issues
        issues_list = [issue.description for issue in review_result.issues]
        refactor_result = await reviewer.refactor_code(
            code=code,
            language=lang_value,
            issues=issues_list if issues_list else None
        )
        
        # Combine results
        return ReviewAndRefactorResponse(
            summary=review_result.summary,
            rating=review_result.rating,
            issues=review_result.issues,
            refactored_code=refactor_result.get("fixed_code", "// Refactoring failed"),
            changes_made=refactor_result.get("changes", [])
        )
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be UTF-8 encoded",
        ) from exc
    except UpstreamTimeoutError as exc:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(exc)) from exc
    except UpstreamServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
