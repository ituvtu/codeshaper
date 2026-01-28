# Architecture Documentation

Цей документ описує архітектуру LLM API і його компоненти.

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        User / Client                         │
└───────────────────────────┬─────────────────────────────────┘
                            │
                     HTTP(S) │
                            │
        ┌───────────────────▼────────────────────┐
        │                                        │
        │    Nginx (Reverse Proxy)               │
        │  • SSL/TLS termination                 │
        │  • Load balancing                      │
        │  • Rate limiting                       │
        │  • Static file serving                 │
        │                                        │
        └───────────────────┬────────────────────┘
                            │
        ┌───────────────────▼────────────────────┐
        │                                        │
        │         FastAPI Application            │
        │                                        │
        │  ┌──────────────────────────────────┐  │
        │  │      API Routes Layer            │  │
        │  │  • /health                       │  │
        │  │  • /api/v1/review                │  │
        │  │  • /api/v1/refactor              │  │
        │  │  • /api/v1/review-and-refactor   │  │
        │  └──────────────────────────────────┘  │
        │                                        │
        │  ┌──────────────────────────────────┐  │
        │  │    Business Logic Layer          │  │
        │  │  • Code analysis                 │  │
        │  │  • LLM prompt generation         │  │
        │  │  • Response parsing              │  │
        │  │  • Language detection            │  │
        │  └──────────────────────────────────┘  │
        │                                        │
        │  ┌──────────────────────────────────┐  │
        │  │      Infrastructure Layer        │  │
        │  │  • HTTP client (httpx)           │  │
        │  │  • LLM API client                │  │
        │  │  • Error handling                │  │
        │  │  • Retry logic                   │  │
        │  └──────────────────────────────────┘  │
        │                                        │
        └───────────────────┬────────────────────┘
                            │
        ┌───────────────────┴─────────────┬─────────────────────┐
        │                                 │                     │
    ┌───▼────┐                      ┌────▼──────┐      ┌────────▼────┐
    │         │                      │           │      │             │
    │  Redis  │                      │ PostgreSQL│      │  Groq API   │
    │         │                      │           │      │             │
    │ Caching │                      │ Database  │      │    LLM      │
    │ Sessions│                      │           │      │             │
    │ Queues  │                      │           │      │  llama-3.1  │
    │         │                      │           │      │             │
    └─────────┘                      └───────────┘      └─────────────┘
```

---

## Layer Architecture

### 1. API Routes Layer (`app/api/routes.py`)

**Зобов'язання:**
- Прийняття HTTP запитів
- Валідація input даних
- Обробка multipart/form-data
- Повернення JSON відповідей
- Обробка помилок на рівні API

**Основні функції:**
```python
@router.get("/health")
async def health_check() -> dict

@router.post("/api/v1/review")
async def review_code(file: UploadFile, language: str = None) -> ReviewResponse

@router.post("/api/v1/refactor")
async def refactor_code(file: UploadFile, language: str = None) -> RefactorResponse

@router.post("/api/v1/review-and-refactor")
async def review_and_refactor_code(file: UploadFile, language: str = None) -> CombinedResponse
```

**Відповідальність:**
- ✅ HTTP заголовки та status codes
- ✅ Валідація content-type
- ✅ Обмеження розміру файлу
- ❌ Не повинна містити бізнес логіку

---

### 2. Business Logic Layer (`app/services/`)

#### `reviewer.py`

**Зобов'язання:**
- Аналіз коду
- Генерація промптів
- Парсинг LLM відповідей
- Підготовка результатів

**Key Methods:**
```python
class CodeReviewer:
    async def review(code: str, language: str) -> ReviewResult
    async def refactor(code: str, language: str) -> RefactorResult
    async def analyze(code: str, language: str) -> AnalysisResult
    
    def _detect_language(filename: str) -> str
    def _generate_review_prompt(code: str, language: str) -> str
    def _parse_review_json(response: str) -> dict
```

**Архітектура:**
```
Code Input
    │
    ├─► Language Detection
    │
    ├─► Prompt Generation
    │
    ├─► LLM API Call (via llm_client)
    │
    ├─► Response Parsing (regex-based for robustness)
    │
    └─► Result Preparation
        │
        └─► ReviewResult (pydantic model)
```

---

### 3. Infrastructure Layer

#### `llm_client.py`

**Зобов'язання:**
- HTTP комунікація з Groq API
- Управління connection pooling
- Retry logic та exponential backoff
- Обробка API errors

**Key Methods:**
```python
class GroqClient:
    async def send_message(prompt: str, model: str) -> str
    async def __aenter__() -> GroqClient
    async def __aexit__() -> None
```

**Retry Strategy:**
```
Request
  │
  ├─ Success (200) → Return response
  │
  ├─ Retry (429, 500, 503) → Wait + Retry (max 3 times)
  │   │
  │   ├─ Attempt 1: Wait 1 second
  │   ├─ Attempt 2: Wait 2 seconds
  │   ├─ Attempt 3: Wait 4 seconds
  │   │
  │   └─ Still fails → Raise error
  │
  └─ Fatal error (401, 403, 404) → Raise immediately
```

#### `dependencies.py`

**Зобов'язання:**
- Dependency injection
- Configuration management
- Resource initialization

**Key Providers:**
```python
async def get_reviewer() -> CodeReviewer
async def get_llm_client() -> GroqClient
```

---

### 4. Configuration Layer (`app/core/`)

#### `config.py`

**Зобов'язання:**
- Завантаження environment variables
- Валідація конфігурації
- Значення за замовчуванням

**Configuration:**
```python
class Settings(BaseSettings):
    API_KEY: str              # Groq API key
    MODEL: str = "llama-3.1-8b-instant"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "info"
    REDIS_URL: str = "redis://localhost:6379/0"
    POSTGRES_URL: str = ""
```

#### `exceptions.py`

**Зобов'язання:**
- Визначення custom exceptions
- Обробка помилок

```python
class CodeReviewError(Exception):
    """Base exception"""

class LLMAPIError(CodeReviewError):
    """LLM API related errors"""

class InvalidLanguageError(CodeReviewError):
    """Unsupported language"""

class JSONParseError(CodeReviewError):
    """Failed to parse LLM response"""
```

---

### 5. Data Models (`app/schemas/`)

**Назначення:**
- Pydantic моделі для валідації
- Сериализация/десериализація JSON
- Type hints та документація

```python
class ReviewResult(BaseModel):
    summary: str
    rating: int  # 0-10
    issues: list[Issue]

class Issue(BaseModel):
    severity: Literal["error", "warning", "info"]
    line: int
    description: str

class RefactorResult(BaseModel):
    refactored_code: str
    changes: list[str]

class CombinedResult(ReviewResult, RefactorResult):
    pass
```

---

## Data Flow

### 1. Code Review Flow

```
Client Request
    │
    ├─ File upload with language
    │
    ▼
[API Routes]
    │
    ├─ Parse multipart/form-data
    ├─ Detect language from filename
    ├─ Validate file size
    │
    ▼
[CodeReviewer.review()]
    │
    ├─ Read file content
    ├─ Generate review prompt with language-specific tips
    ├─ Call LLM
    │
    ▼
[GroqClient.send_message()]
    │
    ├─ Create HTTP request to Groq API
    ├─ Include retry logic
    ├─ Return JSON response
    │
    ▼
[Parse Response]
    │
    ├─ Extract JSON from possibly malformed response
    ├─ Validate against Pydantic model
    ├─ Return ReviewResult
    │
    ▼
[API Response]
    │
    └─ Return JSON to client with 200 OK
```

### 2. Refactoring Flow

```
Similar to review, but:
    - Generate refactoring-specific prompt
    - Parse refactored code from response
    - Validate Python/JS/etc. syntax
    - Return RefactorResult
```

### 3. Combined Flow

```
Client Request
    │
    ▼
Run review() in parallel with refactor()
    │
    ├─ review() → ReviewResult
    ├─ refactor() → RefactorResult
    │
    ▼
Merge results into CombinedResult
    │
    └─ Return to client
```

---

## Error Handling

### Error Hierarchy

```
Exception
├── CodeReviewError
│   ├── LLMAPIError
│   │   ├── API Key Invalid (401)
│   │   ├── Rate Limited (429)
│   │   ├── Server Error (500)
│   │   └── Service Unavailable (503)
│   │
│   ├── InvalidLanguageError
│   ├── JSONParseError
│   └── FileSizeError
│
└── Standard Python Exceptions
    ├── ValueError
    ├── TypeError
    └── etc.
```

### Response Error Format

```json
{
  "detail": "Error message here",
  "status_code": 400,
  "error_type": "InvalidLanguageError"
}
```

---

## Performance Considerations

### Caching Strategy

```
Request
  │
  ├─ Check Redis cache
  │   │
  │   ├─ Hit → Return cached result
  │   │
  │   └─ Miss → Continue to LLM
  │
  ▼
Call LLM
  │
  ▼
Cache result (TTL: 1 hour)
  │
  └─ Return to client
```

### Async/Await Pattern

```python
# All I/O operations are async
@router.post("/api/v1/review")
async def review_code(...):
    # Non-blocking:
    reviewer = await get_reviewer()
    result = await reviewer.review(code, language)
    
    # Can handle many concurrent requests
    # without blocking threads
```

### Concurrency Model

```
Nginx (worker_connections: 1024)
    │
    ├─ Request 1 ──► FastAPI ──► Groq API
    ├─ Request 2 ──► FastAPI ──► Groq API
    ├─ Request 3 ──► FastAPI ──► Groq API
    └─ ...
    
Each request uses single thread with async/await
Maximum: 1024 concurrent connections
```

---

## Security Considerations

### Authentication & Authorization
- ❌ Currently no authentication (stateless API)
- 🔜 Future: API key validation, JWT tokens

### Input Validation
- ✅ File size limits (5MB default)
- ✅ Language whitelist
- ✅ Content-Type validation
- ✅ Pydantic schema validation

### Secrets Management
- ✅ API keys in environment variables
- ✅ Never logged or exposed
- ✅ .env files in .gitignore

### Rate Limiting
- ✅ Nginx rate limiting per IP
- ✅ API burst limits

---

## Testing Architecture

### Test Pyramid

```
          /\              Unit Tests (70%)
         /  \             - Service logic
        /____\            - Utilities
       /      \           
      /________\          Integration Tests (20%)
     /          \         - API endpoints with mocks
    /____________\        
   /              \       E2E Tests (10%)
  /________________\      - Full stack if applicable
```

### Mocking Strategy

```python
# Mock external LLM API
@pytest.fixture
def mock_llm(respx_mock):
    respx_mock.post("https://api.groq.com/...",).mock(
        return_value=httpx.Response(200, json={
            "choices": [{"message": {"content": '{"summary": "..."}'}}]
        })
    )
```

---

## Deployment Architecture

### Development (`docker-compose.dev.yml`)
```
Client:8000 → FastAPI (hot reload)
                │
                ├─ Redis:6379
                └─ (no reverse proxy)
```

### Production (`docker-compose.prod.yml`)
```
Client:80/443 → Nginx (reverse proxy, SSL)
                    │
                    ├─ FastAPI:8000 (uvicorn)
                    │   │
                    │   ├─ Redis:6379 (cache)
                    │   └─ PostgreSQL:5432 (data)
                    │
                    ├─ Prometheus:9090 (metrics)
                    └─ Grafana:3000 (visualization)
```

---

## Scalability

### Horizontal Scaling

```
                    ┌──────────────┐
                    │   Nginx      │
                    │ Load Balancer│
                    └──────┬───────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
    ┌───▼───┐          ┌───▼───┐         ┌───▼───┐
    │ API 1 │          │ API 2 │         │ API 3 │
    │ Pod   │          │ Pod   │         │ Pod   │
    └───┬───┘          └───┬───┘         └───┬───┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                    ┌──────▼───────┐
                    │ Redis Shared │
                    │ (cache)      │
                    └──────────────┘
```

### Vertical Scaling

```yaml
# Increase resources per container
resources:
  limits:
    cpus: '4'        # was 2
    memory: 4G       # was 2G
  reservations:
    cpus: '2'
    memory: 2G
```

---

## Monitoring & Observability

### Metrics Collection

```
FastAPI
  │
  ├─ Prometheus client
  │   │
  │   └─ Collect metrics:
  │       • Request count
  │       • Request latency
  │       • Error rates
  │       • LLM API response times
  │
  ▼
Prometheus (metrics storage)
  │
  ▼
Grafana (visualization & dashboards)
```

### Logging

```python
# Structured logging
logger.info("Code review started", extra={
    "language": language,
    "file_size": len(code),
    "user_id": user_id
})

# Logs → Container stdout → Docker logs → ELK/Grafana Loki
```

---

## Future Improvements

### Planned Features
- [ ] Database persistence
- [ ] User authentication & API keys
- [ ] Caching layer optimization
- [ ] WebSocket for streaming responses
- [ ] Multi-model support
- [ ] Custom prompt templates
- [ ] A/B testing framework
- [ ] Analytics dashboard

### Potential Optimizations
- [ ] Response streaming for large refactors
- [ ] Batch processing API
- [ ] Request prioritization
- [ ] Smart caching based on language
- [ ] Load balancing across multiple LLM providers

---

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [12 Factor App](https://12factor.net/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)

---

**Last Updated:** January 2024
**Version:** 1.0.0
