# LLM-Powered Code Review API

Professional FastAPI microservice for intelligent code review, refactoring suggestions, and code analysis using Groq's LLM API.

## Features
✨ **Core Features**
- 🔍 Intelligent code review analysis
- 🔧 Automated refactoring suggestions
- ⚡ Combined review & refactor operations
- 🌐 RESTful API with FastAPI
- 📦 Production-ready Docker setup
- 🔄 Hot reload for development
- 🧪 Comprehensive test suite (21+ tests)
- 📊 Multi-language support (.py, .js, .ts, .java, .cpp, .go, .rs, .rb, .php, etc.)

🏗️ **Architecture**
- Clean layering: API routes → Business logic → LLM services
- Async/await throughout for high performance
- Pydantic v2 schemas with strict validation
- Redis caching layer
- Nginx reverse proxy
- PostgreSQL database ready

## Quick Start

### Prerequisites
- Python 3.11+ or Docker
- Groq API key ([get here](https://console.groq.com/keys))

### Local Development

```bash
# 1. Clone repository
git clone https://github.com/yourusername/llm-api.git
cd llm-api

# 2. Install dependencies
poetry install

# 3. Setup environment
cp .env.example .env
# Edit .env and add your Groq API key

# 4. Run development server
poetry run uvicorn app.main:app --reload

# 5. Run tests
poetry run pytest tests/ -v
```

Visit:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Docker Development

```bash
# With hot reload and Redis
docker-compose -f deployment/docker-compose.dev.yml up

# Run tests
docker-compose -f deployment/docker-compose.dev.yml exec api poetry run pytest tests/
```

### Docker Production

```bash
# Full stack with Nginx, Redis, PostgreSQL
docker-compose -f deployment/docker-compose.prod.yml up -d

# Check status
docker-compose ps
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed deployment instructions.

## API Endpoints

### Health Check
```bash
GET /health
```
Returns server health status.

### Code Review
```bash
POST /api/v1/review
Content-Type: multipart/form-data

Parameters:
  - file: Code file to review (required)
  - language: Programming language (auto-detected from extension)

Response:
{
  "summary": "Code review analysis...",
  "rating": 8,
  "issues": [
    {
      "severity": "warning",
      "line": 42,
      "description": "Missing error handling"
    }
  ]
}
```

### Code Refactoring
```bash
POST /api/v1/refactor
Content-Type: multipart/form-data

Parameters:
  - file: Code file to refactor (required)
  - language: Programming language (auto-detected)

Response:
{
  "refactored_code": "improved code here...",
  "changes": ["Added type hints", "Optimized loop"]
}
```

### Combined Review & Refactor
```bash
POST /api/v1/review-and-refactor
Content-Type: multipart/form-data

Parameters:
  - file: Code file (required)
  - language: Programming language (auto-detected)

Response:
{
  "summary": "Review analysis...",
  "rating": 8,
  "issues": [...],
  "refactored_code": "improved code...",
  "changes": [...]
}
```

## Configuration

Environment variables (`.env`):

```bash
# LLM Configuration
API_KEY=gsk_your_groq_api_key          # Required
MODEL=llama-3.1-8b-instant             # Default model

# Server
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=info                         # debug, info, warning, error

# Cache & Database
REDIS_URL=redis://localhost:6379/0
POSTGRES_URL=postgresql://user:pass@localhost/db

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600
```

See [deployment/.env.example](deployment/.env.example) for full configuration template.

## Development Commands

Use `Makefile` for convenient commands:

```bash
make help              # Show all commands
make install           # Install dependencies
make dev              # Run development server
make test             # Run tests
make test-cov         # Tests with coverage
make lint             # Run linters
make format           # Format code
make docker-dev       # Docker development
make docker-prod      # Docker production
make clean            # Clean cache files
```

## Project Structure

```
llm-api/
├── app/
│   ├── main.py                 # FastAPI app initialization
│   ├── api/
│   │   ├── routes.py          # API endpoints
│   │   └── dependencies.py    # Dependency injection
│   ├── services/
│   │   ├── reviewer.py        # Business logic
│   │   └── llm_client.py      # Groq API client
│   ├── schemas/
│   │   └── review.py          # Pydantic models
│   ├── core/
│   │   ├── config.py          # Configuration
│   │   └── exceptions.py      # Custom exceptions
│   └── static/
│       └── index.html         # Web GUI
├── tests/
│   └── test_api.py            # Comprehensive tests (21+)
├── deployment/                # All deployment configs
│   ├── docker-compose.dev.yml
│   ├── docker-compose.prod.yml
│   ├── nginx.conf
│   ├── prometheus.yml
│   └── .env.example
├── docs/                      # Documentation
│   ├── ARCHITECTURE.md
│   └── DEPLOYMENT.md
├── Dockerfile                 # Multi-stage build
├── docker-compose.yml         # Basic compose (quick start)
├── Makefile                   # Convenient commands
└── README.md                  # This file
```

## Testing

```bash
# Run all tests
poetry run pytest tests/ -v

# Run with coverage
poetry run pytest tests/ -v --cov=app --cov-report=html

# Watch mode (auto-run on changes)
poetry run ptw tests/
```

Current test coverage: **21/21 passing** ✅

## Docker

### Multi-stage Build
- **Builder stage**: Installs Poetry, builds dependencies
- **Runtime stage**: Minimal Python image with only needed packages
- **Security**: Non-root user (appuser:1000)
- **Signals**: Tini for proper PID 1 handling
- **Health checks**: Built-in healthchecks

### Production Stack
- **API**: FastAPI with uvicorn
- **Reverse Proxy**: Nginx with SSL, caching, rate limiting
- **Cache**: Redis for session/response caching
- **Database**: PostgreSQL (optional)
- **Monitoring**: Prometheus + Grafana
- **Logging**: Structured JSON logging

## CI/CD

GitHub Actions pipeline automated on every push to `main` or `develop` branches and on pull requests:

### Workflow: `ci.yml` - Testing Pipeline
Runs on every push and PR:
- **Test matrix**: Python 3.11, 3.12, 3.13 (parallel)
- **Poetry cache**: Speeds up dependency installation
- **Linting**: Ruff for code quality checks
- **Type checking**: Mypy for type safety
- **Format check**: Black for code style consistency
- **Tests**: Full pytest suite with coverage
- **Coverage upload**: Reports to Codecov
- **Docker build**: Validates Dockerfile (no push)

### Workflow: `quality.yml` - Code Quality
Runs on every push and PR:
- **Import sorting**: isort validation
- **Code formatting**: Black format checking
- **Linting**: Ruff analysis
- **Coverage report**: Detailed coverage metrics
- **Coverage upload**: Tracks coverage over time

### How to use:
1. **Push to main/develop** → CI runs automatically
2. **Create Pull Request** → Tests & quality checks block merge if failing
3. **View results** → Check Actions tab in GitHub

### Local testing before push:
```bash
# Run all checks locally
poetry run pytest tests/ -v
poetry run ruff check app/
poetry run black --check app/
poetry run mypy app/ --ignore-missing-imports
```

### GitHub Secrets (if needed for future deployment):
Currently not required. If you plan Docker Hub deployment later:
- `DOCKER_USERNAME`
- `DOCKER_PASSWORD`

See [`.github/workflows/`](.github/workflows/) for workflow details.

## Performance

- **Request timeout**: 30s
- **Concurrent connections**: 1024 (Nginx worker connections)
- **Memory limit**: 2GB (production)
- **CPU limit**: 2 cores (production)
- **Redis eviction**: allkeys-lru with 512MB max
- **Gzip compression**: Enabled for responses

## Security Features

- ✅ Non-root container user
- ✅ HTTPS/SSL support (nginx)
- ✅ Rate limiting per IP
- ✅ CORS protection
- ✅ X-Frame-Options headers
- ✅ X-Content-Type-Options headers
- ✅ Environment variable validation
- ✅ SQL injection prevention (ORM ready)

## Troubleshooting

### API not responding
```bash
docker-compose logs api
docker-compose ps
docker stats
```

### Out of memory
Increase limits in `docker-compose.yml`:
```yaml
deploy:
  resources:
    limits:
      memory: 4G
```

### Database connection issues
Check `REDIS_URL` and `POSTGRES_URL` in `.env`:
```bash
docker-compose exec redis redis-cli ping
docker-compose exec postgres psql -U user -c "SELECT 1"
```

See [DEPLOYMENT.md](DEPLOYMENT.md#troubleshooting) for more.

## Contributing

1. Fork repository
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open Pull Request

## License

MIT License - see LICENSE file

## Support

- 📖 [Deployment Guide](docs/DEPLOYMENT.md)
- 🏗️ [Architecture Guide](docs/ARCHITECTURE.md)
- 🐛 [Issue Tracker](https://github.com/yourusername/llm-api/issues)
- 💬 [Discussions](https://github.com/yourusername/llm-api/discussions)
- 📧 Email: support@example.com

---

**Built with ❤️ using FastAPI, Groq API, and Docker**
