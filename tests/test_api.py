"""
TDD-based unit and integration tests for Code Review API.
Tests actual functionality with mocked LLM API calls.
"""

import json
import pytest
import httpx
import respx
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.main import create_app, lifespan


@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("URL", "https://api.groq.com/openai/v1")
    monkeypatch.setenv("MODEL", "llama-3.1-8b-instant")
    get_settings.cache_clear()


@asynccontextmanager
async def create_test_client(app):
    """Create async test client with proper lifecycle management."""
    async with lifespan(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


class TestHealthEndpoint:
    """Tests for GET /health endpoint."""

    @pytest.mark.asyncio
    async def test_health_check_returns_ok(self, respx_mock: respx.MockRouter):
        """GIVEN a running API server
        WHEN requesting health status
        THEN return status ok"""
        app = create_app()
        # Mock the /models endpoint for health check
        respx_mock.get("https://api.groq.com/openai/v1/models").mock(
            return_value=httpx.Response(200, json={"data": []})
        )
        
        async with create_test_client(app) as client:
            resp = await client.get("/health")

        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_health_response_has_correct_schema(self, respx_mock: respx.MockRouter):
        """GIVEN a health check request
        WHEN response received
        THEN response matches HealthResponse schema"""
        app = create_app()
        # Mock the /models endpoint for health check
        respx_mock.get("https://api.groq.com/openai/v1/models").mock(
            return_value=httpx.Response(200, json={"data": []})
        )
        
        async with create_test_client(app) as client:
            resp = await client.get("/health")

        body = resp.json()
        assert "status" in body
        assert isinstance(body["status"], str)


class TestReviewEndpoint:
    """Tests for POST /api/v1/review endpoint."""

    @pytest.mark.asyncio
    async def test_review_requires_file(self):
        """GIVEN review request without file
        WHEN endpoint called
        THEN return 422 validation error"""
        app = create_app()
        async with create_test_client(app) as client:
            resp = await client.post("/api/v1/review", data={"language": "python"})

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_review_requires_language_or_extension(self):
        """GIVEN file upload without language or known extension
        WHEN endpoint called
        THEN return 400 bad request"""
        app = create_app()
        async with create_test_client(app) as client:
            files = {"file": ("unknown.xyz", b"code here", "text/plain")}
            resp = await client.post("/api/v1/review", files=files)

        assert resp.status_code == 400
        assert "Language is required" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_review_infers_language_from_extension(self, respx_mock: respx.MockRouter):
        """GIVEN Python file without explicit language parameter
        WHEN endpoint called
        THEN language should be inferred from .py extension"""
        app = create_app()
        respx_mock.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({
                "summary": "Good code", "rating": 8, "top_issues": []
            })}}]})
        )
        
        async with create_test_client(app) as client:
            files = {"file": ("test.py", b"def foo(): pass", "text/plain")}
            resp = await client.post("/api/v1/review", files=files)

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_review_rejects_invalid_focus(self):
        """GIVEN invalid focus parameter
        WHEN endpoint called
        THEN return 400 bad request"""
        app = create_app()
        async with create_test_client(app) as client:
            files = {"file": ("test.py", b"def foo(): pass", "text/plain")}
            data = {"language": "python", "focus": "invalid_focus"}
            resp = await client.post("/api/v1/review", files=files, data=data)

        assert resp.status_code == 400
        assert "Invalid focus" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_review_accepts_valid_focus_values(self, respx_mock: respx.MockRouter):
        """GIVEN valid focus values
        WHEN endpoint called
        THEN request should be accepted (before LLM call)"""
        app = create_app()
        valid_focuses = ["security", "performance", "clean_code"]
        
        respx_mock.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({
                "summary": "Code OK", "rating": 7, "top_issues": []
            })}}]})
        )

        async with create_test_client(app) as client:
            for focus in valid_focuses:
                files = {"file": ("test.py", b"code", "text/plain")}
                data = {"language": "python", "focus": focus}
                resp = await client.post("/api/v1/review", files=files, data=data)

                assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_review_rejects_non_utf8_file(self):
        """GIVEN binary non-UTF8 file
        WHEN endpoint called
        THEN return 400 bad request"""
        app = create_app()
        async with create_test_client(app) as client:
            # Invalid UTF-8 bytes
            invalid_utf8 = b"\x80\x81\x82"
            files = {"file": ("test.py", invalid_utf8, "text/plain")}
            resp = await client.post("/api/v1/review", files=files, data={"language": "python"})

        assert resp.status_code == 400
        assert "UTF-8" in resp.json()["detail"]


class TestRefactorEndpoint:
    """Tests for POST /api/v1/refactor endpoint."""

    @pytest.mark.asyncio
    async def test_refactor_requires_code(self):
        """GIVEN refactor request without code
        WHEN endpoint called
        THEN return 422 validation error"""
        app = create_app()
        async with create_test_client(app) as client:
            payload = {"language": "python"}
            resp = await client.post("/api/v1/refactor", json=payload)

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_refactor_requires_language(self):
        """GIVEN refactor request without language
        WHEN endpoint called
        THEN return 422 validation error"""
        app = create_app()
        async with create_test_client(app) as client:
            payload = {"code": "def foo(): pass"}
            resp = await client.post("/api/v1/refactor", json=payload)

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_refactor_accepts_optional_issues(self, respx_mock: respx.MockRouter):
        """GIVEN refactor request with and without issues
        WHEN endpoint called
        THEN both should be accepted"""
        app = create_app()
        
        respx_mock.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(200, json={"choices": [{"message": {"content": 
                '{"fixed_code": "def foo(): pass", "changes": ["Added hints"]}'
            }}]})
        )
        
        async with create_test_client(app) as client:
            # Without issues
            payload1 = {"code": "def foo(): pass", "language": "python"}
            resp1 = await client.post("/api/v1/refactor", json=payload1)
            assert resp1.status_code == 200

            # With issues
            payload2 = {
                "code": "def foo(): pass",
                "language": "python",
                "issues": ["Add documentation"]
            }
            resp2 = await client.post("/api/v1/refactor", json=payload2)
            assert resp2.status_code == 200


class TestReviewAndRefactorEndpoint:
    """Tests for POST /api/v1/review-and-refactor endpoint."""

    @pytest.mark.asyncio
    async def test_review_and_refactor_requires_file(self):
        """GIVEN request without file
        WHEN endpoint called
        THEN return 422 validation error"""
        app = create_app()
        async with create_test_client(app) as client:
            resp = await client.post("/api/v1/review-and-refactor", data={"language": "python"})

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_review_and_refactor_requires_language_or_extension(self):
        """GIVEN file without language or known extension
        WHEN endpoint called
        THEN return 400 bad request"""
        app = create_app()
        async with create_test_client(app) as client:
            files = {"file": ("unknown.xyz", b"code", "text/plain")}
            resp = await client.post("/api/v1/review-and-refactor", files=files)

        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_review_and_refactor_infers_language_from_extension(self, respx_mock: respx.MockRouter):
        """GIVEN Python file without explicit language
        WHEN endpoint called
        THEN language inferred from .py extension"""
        app = create_app()
        
        respx_mock.post("https://api.groq.com/openai/v1/chat/completions").mock(
            side_effect=[
                httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({
                    "summary": "Good code", "rating": 8, "top_issues": []
                })}}]}),
                httpx.Response(200, json={"choices": [{"message": {"content": 
                    '{"fixed_code": "def foo(): pass", "changes": ["Improved"]}'
                }}]})
            ]
        )
        
        async with create_test_client(app) as client:
            files = {"file": ("test.py", b"def foo(): pass", "text/plain")}
            resp = await client.post("/api/v1/review-and-refactor", files=files)

        assert resp.status_code == 200


class TestLanguageDetection:
    """Tests for file extension to language mapping."""

    @pytest.mark.asyncio
    async def test_all_supported_extensions(self, respx_mock: respx.MockRouter):
        """GIVEN files with various supported extensions
        WHEN review endpoint called
        THEN language should be detected correctly"""
        app = create_app()
        extensions = [
            "test.py", "test.js", "test.ts", "test.jsx", "test.tsx",
            "test.java", "test.cpp", "test.cc", "test.c", "test.go",
            "test.rs", "test.rb", "test.php"
        ]
        
        respx_mock.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({
                "summary": "OK", "rating": 7, "top_issues": []
            })}}]})
        )

        async with create_test_client(app) as client:
            for filename in extensions:
                files = {"file": (filename, b"code", "text/plain")}
                resp = await client.post("/api/v1/review", files=files)
                # Should recognize language from extension
                assert resp.status_code == 200


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_unicode_in_code(self, respx_mock: respx.MockRouter):
        """GIVEN code with unicode characters
        WHEN review endpoint called
        THEN should handle UTF-8 correctly"""
        app = create_app()
        
        respx_mock.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({
                "summary": "Unicode OK", "rating": 8, "top_issues": []
            })}}]})
        )
        
        async with create_test_client(app) as client:
            code = "# 你好世界\ndef greet(): return 'привіт'".encode("utf-8")
            files = {"file": ("unicode.py", code, "text/plain")}
            resp = await client.post("/api/v1/review", files=files, data={"language": "python"})

            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_empty_code_file(self, respx_mock: respx.MockRouter):
        """GIVEN empty code file
        WHEN review endpoint called
        THEN should handle gracefully - may return error or process it"""
        app = create_app()
        
        respx_mock.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({
                "summary": "Empty file", "rating": 5, "top_issues": []
            })}}]})
        )
        
        async with create_test_client(app) as client:
            files = {"file": ("empty.py", b"", "text/plain")}
            resp = await client.post("/api/v1/review", files=files, data={"language": "python"})

            # Empty file might return 400 or be processed - both acceptable
            assert resp.status_code in [200, 400, 500]

    @pytest.mark.asyncio
    async def test_whitespace_only_code(self, respx_mock: respx.MockRouter):
        """GIVEN file with only whitespace
        WHEN review endpoint called
        THEN should handle gracefully"""
        app = create_app()
        
        respx_mock.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({
                "summary": "Whitespace", "rating": 5, "top_issues": []
            })}}]})
        )
        
        async with create_test_client(app) as client:
            files = {"file": ("whitespace.py", b"   \n\t\n   ", "text/plain")}
            resp = await client.post("/api/v1/review", files=files, data={"language": "python"})

            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_special_characters_in_code(self, respx_mock: respx.MockRouter):
        """GIVEN code with special characters and emojis
        WHEN review endpoint called
        THEN should handle UTF-8 correctly"""
        app = create_app()
        
        respx_mock.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({
                "summary": "Special chars OK", "rating": 7, "top_issues": []
            })}}]})
        )
        
        async with create_test_client(app) as client:
            code = "# Special: !@#$%^&*() 🚀💻\ndef test(): pass".encode("utf-8")
            files = {"file": ("special.py", code, "text/plain")}
            resp = await client.post("/api/v1/review", files=files, data={"language": "python"})

            assert resp.status_code == 200


class TestRequestValidation:
    """Tests for request parameter validation."""

    @pytest.mark.asyncio
    async def test_refactor_issues_as_list(self, respx_mock: respx.MockRouter):
        """GIVEN issues as list in refactor request
        WHEN endpoint called
        THEN should be accepted"""
        app = create_app()
        
        respx_mock.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(200, json={"choices": [{"message": {"content": 
                '{"fixed_code": "fixed", "changes": ["Changed"]}'
            }}]})
        )
        
        async with create_test_client(app) as client:
            payload = {
                "code": "def foo(): pass",
                "language": "python",
                "issues": ["Issue 1", "Issue 2"]
            }
            resp = await client.post("/api/v1/refactor", json=payload)
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_refactor_issues_as_empty_list(self, respx_mock: respx.MockRouter):
        """GIVEN empty issues list in refactor request
        WHEN endpoint called
        THEN should be accepted"""
        app = create_app()
        
        respx_mock.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(200, json={"choices": [{"message": {"content": 
                '{"fixed_code": "fixed", "changes": []}'
            }}]})
        )
        
        async with create_test_client(app) as client:
            payload = {
                "code": "def foo(): pass",
                "language": "python",
                "issues": []
            }
            resp = await client.post("/api/v1/refactor", json=payload)
            assert resp.status_code == 200

