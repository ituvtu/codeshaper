# CI/CD Pipeline Documentation

## Overview

This project uses GitHub Actions for continuous integration and automated testing. The pipeline ensures code quality, tests pass, and Docker builds successfully on every push.

## Workflows

### 1. CI Pipeline (`ci.yml`)

**Triggers:** 
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

**Jobs:**

#### Test Job
Runs on a matrix of Python versions (3.11, 3.12, 3.13) in parallel:

1. **Setup**
   - Checkout code
   - Set up Python version
   - Cache Poetry installation (speeds up future runs)
   - Install Poetry
   - Cache virtual environment dependencies

2. **Code Quality Checks** (non-blocking)
   - Ruff: Fast Python linter
   - Mypy: Static type checker
   - Black: Code formatter check

3. **Testing**
   - Run pytest with coverage
   - Generate coverage reports (XML format)
   - Upload to Codecov

4. **Pull Request Comments**
   - Add comment to PR with test results for each Python version

#### Docker Build Job
Runs after tests pass, only on push to `main`:
- Validates Dockerfile builds correctly
- Uses GitHub Actions cache for faster builds
- Does not push to registry (local-only verification)

### 2. Code Quality (`quality.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

**Jobs:**

#### Code Quality Job
- **isort**: Check import sorting
- **Black**: Verify code formatting
- **Ruff**: Run linter

#### Coverage Job
- Run full test suite
- Generate coverage reports
- Display coverage summary
- Upload to Codecov (optional)

## How It Works

### When you push code to GitHub:

```
1. GitHub detects push → Triggers workflows
2. ci.yml runs → Tests on 3 Python versions in parallel
   ├─ Python 3.11 tests
   ├─ Python 3.12 tests
   └─ Python 3.13 tests
3. quality.yml runs → Code quality checks
4. Docker build → Validates Dockerfile (no push)
5. All pass ✅ → Your code is ready
```

### When you create a Pull Request:

```
1. Same workflows run
2. GitHub shows ✅ if all pass, ❌ if any fail
3. Cannot merge PR if required checks fail
4. Comments added with results
5. Fix issues, push again → Auto-rerun
```

## Local Testing

Before pushing, run these checks locally:

```bash
# Install dependencies
poetry install

# Run tests
poetry run pytest tests/ -v --cov=app

# Format code
poetry run black app/ tests/

# Check formatting (dry run)
poetry run black --check app/

# Lint code
poetry run ruff check app/

# Type check
poetry run mypy app/ --ignore-missing-imports

# Sort imports
poetry run isort app/ tests/

# All at once (Makefile)
make lint
make test
```

## GitHub Actions Dashboard

View workflow runs:
1. Go to your GitHub repository
2. Click **Actions** tab
3. See all workflow runs
4. Click a run to see detailed logs
5. Expand each job to see step-by-step output

## Troubleshooting

### Tests fail locally but pass in CI
- Different Python version (use 3.13 by default)
- Missing environment file (copy `.env.example`)
- Stale cache: `rm -rf .pytest_cache venv`

### CI tests pass but my IDE shows errors
- Mypy cache: `rm -rf .mypy_cache`
- Python path: Ensure virtual environment is selected in IDE
- Pylance: Reload window with `Ctrl+Shift+P` → "Developer: Reload Window"

### Slow CI runs
- Poetry cache: Check GitHub Actions cache settings
- Python matrix: Consider removing Python 3.11 if not needed
- Dependencies: Reduce transitive dependencies

### Docker build fails in CI
- Check `.dockerignore` includes `.venv`, `__pycache__`, `poetry.lock`
- Ensure `Dockerfile` is in root directory
- Test locally: `docker build -t llm-api:test .`

## Future Improvements

When ready to deploy:

1. **Docker Hub push:**
   - Add `DOCKER_USERNAME` and `DOCKER_PASSWORD` secrets to GitHub
   - Uncomment Docker push step in `ci.yml`

2. **Deployment:**
   - Create `deploy.yml` workflow for deployment
   - Use SSH keys or deployment tokens
   - Trigger on version tags

3. **Notifications:**
   - Slack notifications on failure
   - Email summaries
   - Custom status checks

## Secrets Management

Currently not using any secrets (no Docker Hub push). If needed later:

**To add a secret to GitHub:**
1. Settings → Secrets and variables → Actions
2. New repository secret
3. Name: `SECRET_NAME`
4. Value: Your secret value
5. Use in workflow: `${{ secrets.SECRET_NAME }}`

## Performance Notes

- **Parallel testing**: 3 Python versions run simultaneously (faster)
- **Poetry cache**: Saves ~2 minutes on subsequent runs
- **Docker layer cache**: Speeds up image builds
- **GHA cache**: Stores dependencies for 7 days

Typical CI run: **3-5 minutes** (depending on GitHub's queue)

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Pytest Documentation](https://docs.pytest.org/)
- [Poetry Documentation](https://python-poetry.org/docs/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
