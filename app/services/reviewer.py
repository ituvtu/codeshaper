import json
import re
from textwrap import dedent
from typing import Any

from app.core.exceptions import UpstreamServiceError
from app.schemas.review import ReviewRequest, ReviewResponse
from app.services.llm_client import LLMClient

SYSTEM_PROMPT_SIMPLE = "Analyze code. Return JSON: {\"rating\":1-10,\"summary\":\"text\",\"top_issues\":[\"issue1\",\"issue2\",\"issue3\"]}. No markdown."

SYSTEM_PROMPT_WITH_CODE = "Analyze code. Return JSON: {\"rating\":1-10,\"summary\":\"text\",\"top_issues\":[\"issue1\",\"issue2\"],\"fixed_code\":\"improved code snippet\"}. No markdown. Keep fixed_code short (max 15 lines)."

FEW_SHOT_SIMPLE = "Example: \"eval(input())\" -> {\"rating\":1,\"summary\":\"Critical: eval with user input allows code injection\",\"top_issues\":[\"eval() is dangerous\",\"No validation\",\"Security risk\"]}"

FEW_SHOT_WITH_CODE = "Example: \"eval(input())\" -> {\"rating\":1,\"summary\":\"Critical security issue\",\"top_issues\":[\"eval() dangerous\",\"No validation\"],\"fixed_code\":\"user_input = input()\\nif user_input.isdigit():\\n    result = int(user_input)\\nelse:\\n    raise ValueError('Invalid input')\"}"


class Reviewer:
    def __init__(self, client: LLMClient) -> None:
        self._client = client

    async def ping(self) -> None:
        await self._client.health()

    async def review_code(self, request: ReviewRequest) -> ReviewResponse:
        prompt = f"{FEW_SHOT_SIMPLE}\\n\\nLang: {request.language}\\nCode: {request.code}\\n\\nJSON:"
        
        payload = {
            "model": self._client._settings.openrouter_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT_SIMPLE},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "max_tokens": 512,
        }
        
        raw_response = await self._client.generate(payload)
        content = self._extract_text(raw_response)
        parsed = self._parse_json(content)
        
        return ReviewResponse(
            summary=parsed.get("summary", "Review completed"),
            rating=parsed.get("rating", 5),
            issues=[
                {"severity": "warning", "line": idx + 1, "description": issue}
                for idx, issue in enumerate(parsed.get("top_issues", [])[:5])
            ],
            refactored_code=None
        )

    async def refactor_code(self, code: str, language: str, issues: list[str] | None = None) -> dict[str, Any]:
        """Generate refactored code based on optional issues."""
        if issues:
            issues_text = "\n".join(f"- {issue}" for issue in issues[:5])
            user_prompt = f"""Issues to fix:
{issues_text}

Original code:
{code}

YOUR RESPONSE MUST BE ONLY THIS JSON FORMAT (nothing else):
{{"fixed_code": "...", "changes": ["change1", "change2"]}}

Replace ... with the COMPLETE refactored code. Use \\n for line breaks inside the string."""
        else:
            user_prompt = f"""Original code:
{code}

YOUR RESPONSE MUST BE ONLY THIS JSON FORMAT (nothing else):
{{"fixed_code": "...", "changes": ["change1", "change2"]}}

Replace ... with the COMPLETE refactored code. Use \\n for line breaks inside the string."""
        
        system_prompt = """You are a code refactoring tool. You MUST respond with ONLY a JSON object, no other text.
Format: {"fixed_code": "complete code here", "changes": ["list", "of", "changes"]}
Use \\n for newlines inside the fixed_code string. Do NOT use markdown. Do NOT add explanations."""
        
        payload = {
            "model": self._client._settings.openrouter_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 4096,
        }
        
        raw_response = await self._client.generate(payload)
        content = self._extract_text(raw_response)
        
        # Special parsing for refactor response
        result = self._parse_refactor_json(content)
        return result
    
    def _parse_refactor_json(self, text: str) -> dict[str, Any]:
        """Parse JSON specifically for refactor responses."""
        text = text.strip()
        
        # Remove markdown code fences
        if text.startswith('```'):
            text = re.sub(r'```(?:json)?\s*', '', text)
            text = re.sub(r'```\s*$', '', text)
        
        # The LLM returns prettified JSON with actual newlines in strings
        # We need to parse it more carefully
        
        # Strategy: Use regex to extract fixed_code and changes separately
        # Then reconstruct as valid JSON
        
        # Extract fixed_code (everything between "fixed_code": " and ", "changes")
        fixed_code_match = re.search(r'"fixed_code"\s*:\s*"(.*?)"\s*,\s*"changes"', text, re.DOTALL)
        if not fixed_code_match:
            return {
                "fixed_code": "// Failed to extract refactored code",
                "changes": ["Error: Could not parse response"]
            }
        
        fixed_code = fixed_code_match.group(1)
        
        # Extract changes array (everything between "changes": [ and ])
        changes_match = re.search(r'"changes"\s*:\s*\[(.*?)\]', text, re.DOTALL)
        changes = []
        if changes_match:
            changes_text = changes_match.group(1)
            # Extract individual change strings
            change_items = re.findall(r'"([^"]*)"', changes_text)
            changes = change_items
        
        return {
            "fixed_code": fixed_code,
            "changes": changes
        }

    def _extract_text(self, response: Any) -> str:
        if isinstance(response, dict) and "choices" in response and response["choices"]:
            content = response["choices"][0].get("message", {}).get("content")
            if content:
                return content
        raise UpstreamServiceError("Unexpected LLM response format")

    def _parse_json(self, text: str) -> dict[str, Any]:
        # Remove markdown
        text = text.strip()
        if text.startswith('```'):
            text = re.sub(r'```(?:json)?\s*', '', text)
            text = re.sub(r'```\s*$', '', text)
        
        # Find JSON boundaries
        start = text.find('{')
        end = text.rfind('}')
        if start >= 0 and end > start:
            text = text[start:end + 1]
        
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Fallback
            return {
                "summary": "Unable to parse review",
                "rating": 5,
                "top_issues": ["Review parsing failed"]
            }


def normalize_severity(severity: str):
    from app.schemas.review import SeverityEnum
    return SeverityEnum.warning
