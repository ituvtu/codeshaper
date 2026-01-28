# CodeShaper

Professional FastAPI service for intelligent AI-powered code analysis. Delivers automated code reviews, refactoring suggestions, and quality improvements for Python, JavaScript, TypeScript, Java, and more. Built on Groq LLM with production-ready Docker setup, Redis caching, and Prometheus monitoring. 21+ tests, clean architecture, fully deployment-ready.

## Features

- 🔍 **Intelligent Code Review** - AI-powered analysis with severity ratings and line-specific issues
- 🔧 **Automated Refactoring** - Smart suggestions for code improvements
- ⚡ **Combined Operations** - Review and refactor code in one request
- 🌐 **Multi-Language** - Python, JavaScript, TypeScript, Java, C++, Go, Rust, Ruby, PHP, and more
- 🚀 **Production Ready** - Docker multi-stage builds, health checks, non-root user
- 🔄 **Hot Reload** - Development environment with live code updates
- 📊 **Comprehensive Tests** - 21+ passing tests with coverage reporting
- 🔐 **Secure** - HTTPS/SSL support, rate limiting, input validation

## Quick Start

### Prerequisites
- Python 3.11+ or Docker
- Groq API key ([get here](https://console.groq.com/keys))

### Local Development

```bash
# Clone and setup
git clone https://github.com/ituvtu/codeshaper.git
cd codeshaper
poetry install

# Configure
cp .env.example .env
# Edit .env with your Groq API key

# Run
poetry run uvicorn app.main:app --reload
```

Visit: http://localhost:8000/docs

### Docker

```bash
# Development with hot reload
docker-compose -f deployment/docker-compose.dev.yml up

# Production full stack
docker-compose -f deployment/docker-compose.prod.yml up -d
```

## API Endpoints

### Health Check
```bash
GET /health
```

### Code Review
```bash
POST /api/v1/review
Content-Type: multipart/form-data

Parameters:
  - file: Code file to review
  - language: Programming language (auto-detected)
```

### Code Refactoring
```bash
POST /api/v1/refactor
Content-Type: multipart/form-data

Parameters:
  - file: Code file to refactor
  - language: Programming language (auto-detected)
```

### Combined Review & Refactor
```bash
POST /api/v1/review-and-refactor
Content-Type: multipart/form-data

Parameters:
  - file: Code file
  - language: Programming language (auto-detected)
```

Full examples and response formats: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

## Configuration

Environment variables in `.env`:

```bash
API_KEY=your_groq_api_key_here     # Required
MODEL=llama-3.1-8b-instant         # LLM model
REDIS_URL=redis://localhost:6379   # Cache (optional)
POSTGRES_URL=postgresql://...      # Database (optional)
PORT=8000
LOG_LEVEL=info
```

See [deployment/.env.example](deployment/.env.example) for all options.

## Development

```bash
# Tests
poetry run pytest tests/ -v

# Code quality
make lint       # Linting checks
make format     # Format code
make test-cov   # Tests with coverage

# All commands
make help
```

## Project Structure

```
codeshaper/
├── app/                    # Application code
│   ├── api/routes.py      # API endpoints
│   ├── services/          # Business logic & LLM client
│   └── static/index.html  # Web UI
├── tests/test_api.py      # 21+ comprehensive tests
├── deployment/            # Docker & configs
│   ├── docker-compose.*.yml
│   ├── nginx.conf
│   └── prometheus.yml
├── docs/                  # Full documentation
├── Dockerfile             # Multi-stage build
└── pyproject.toml         # Dependencies
```

## CI/CD

Automated testing and quality checks on every push:
- ✅ Test matrix: Python 3.11, 3.12, 3.13
- ✅ Linting: Ruff, Mypy, Black
- ✅ Coverage reports
- 🐳 Docker build validation
- 📊 Code quality metrics

View workflows: [.github/workflows/](/.github/workflows/)

## Documentation

- 📖 **[Deployment Guide](docs/DEPLOYMENT.md)** - Local, Docker, and production setup
- 🏗️ **[Architecture Guide](docs/ARCHITECTURE.md)** - System design and technical details
- ⚙️ **[CI/CD Guide](docs/CI_CD.md)** - GitHub Actions workflows

## Security

- ✅ Non-root container user
- ✅ HTTPS/SSL ready
- ✅ Rate limiting per IP
- ✅ Input validation
- ✅ CORS protection
- ✅ Environment variable validation

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/improvement`)
3. Make changes and test
4. Push and open Pull Request

All contributions must pass CI/CD checks (tests, linting, coverage).

## License

MIT License - see LICENSE file for details

## Support

- 🐛 [Issue Tracker](https://github.com/ituvtu/codeshaper/issues)
- 💬 [Discussions](https://github.com/ituvtu/codeshaper/discussions)
- 📧 Questions? Open an issue on GitHub

---

**Built with FastAPI, Groq LLM, and Docker**
