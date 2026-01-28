from fastapi import Depends, Request

from app.core.config import Settings, get_settings
from app.services.llm_client import LLMClient
from app.services.reviewer import Reviewer


def get_settings_dep() -> Settings:
    return get_settings()


def get_llm_client(request: Request) -> LLMClient:
    return request.app.state.llm_client


def get_reviewer(request: Request) -> Reviewer:
    return request.app.state.reviewer
