# Deployment Guide

Цей документ описує як розгортати LLM API з використанням Docker та інших інструментів.

## Зміст
1. [Локальна розробка](#локальна-розробка)
2. [Docker для розробки](#docker-для-розробки)
3. [Production розгортання](#production-розгортання)
4. [CI/CD Pipeline](#cicd-pipeline)
5. [Secrets Management](#secrets-management)
6. [Моніторинг та логування](#моніторинг-та-логування)

---

## Локальна розробка

### Вимоги
- Python 3.11+
- Poetry
- Git

### Установка
```bash
# Клонування репозиторію
git clone https://github.com/yourusername/llm-api.git
cd llm-api

# Установка залежностей
poetry install

# Копіювання .env файлу
cp .env.example .env
# Відредагуйте .env і додайте Groq API ключ
```

### Запуск
```bash
# Активація venv та запуск сервера
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# На іншому терміналі для тестування
poetry run pytest tests/ -v
```

API буде доступна на `http://localhost:8000`
Документація: `http://localhost:8000/docs`

---

## Docker для розробки

### Вимоги
- Docker Desktop (або Docker + Docker Compose)
- 4GB+ RAM (рекомендується)

### Розробка з hot reload

```bash
# Скопіюйте .env
cp .env.example .env

# Запустіть compose з hot reload
docker-compose -f docker-compose.dev.yml up

# На іншому терміналі для тестування
docker-compose -f docker-compose.dev.yml exec api poetry run pytest tests/
```

**Особливості:**
- Hot reload при змінах коду в `app/`
- Redis автоматично запускається
- Портове маршрутизування: 8000
- Volumes для швидкого розробки

### Зупинка
```bash
docker-compose -f docker-compose.dev.yml down
```

---

## Production розгортання

### Передумови
- Groq API ключ
- Docker та Docker Compose на сервері
- SSL сертифікат (рекомендується)
- Мінімум 1GB вільної пам'яті

### Підготовка сервера

```bash
# 1. Оновіть систему
sudo apt-get update && sudo apt-get upgrade -y

# 2. Встановіть Docker та Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 3. Завантажте репозиторій
git clone https://github.com/yourusername/llm-api.git /opt/llm-api
cd /opt/llm-api

# 4. Створіть .env для production
cat > .env << EOF
API_KEY=your_groq_api_key_here
MODEL=llama-3.1-8b-instant
REDIS_URL=redis://redis:6379/0
PORT=8000
LOG_LEVEL=info
EOF

# 5. Встановіть права доступу
sudo chown -R $(id -u):$(id -g) /opt/llm-api
```

### Запуск production сервісу

```bash
# Без SSL
docker-compose -f docker-compose.yml up -d

# З SSL (якщо у вас є сертифікати)
# 1. Помістіть cert.pem та key.pem в поточну директорію
# 2. Розкомментуйте SSL секцію в nginx.conf
# 3. Запустіть:
docker-compose -f docker-compose.yml up -d
```

### Перевірка статусу

```bash
# Перевірте статус контейнерів
docker-compose ps

# Перевірте логи API
docker-compose logs api

# Перевірте логи Nginx
docker-compose logs nginx

# Перевірте health endpoint
curl http://localhost/health
```

### Масштабування

```bash
# Збільшіть кількість API інстансів (якщо використовуєте балансер навантаження)
docker-compose up -d --scale api=3

# Або вручну відредагуйте docker-compose.yml і змініть replicas
```

---

## CI/CD Pipeline

### GitHub Actions Setup

1. **Додайте Secrets на GitHub:**
   ```
   Settings → Secrets and variables → Actions
   ```
   Необхідні:
   - `DOCKER_USERNAME` - Docker Hub username
   - `DOCKER_PASSWORD` - Docker Hub password
   - `SERVER_IP` - IP вашого production сервера
   - `DEPLOY_KEY` - SSH приватний ключ

2. **Workflow виконується на:**
   - Push до `main` або `develop`
   - Pull requests
   - Tag push (v1.0.0 format для релізу)

3. **Етапи Pipeline:**
   - ✅ Тестування (Python 3.11, 3.12, 3.13)
   - ✅ Linting (Pylint, Mypy, Black)
   - ✅ Coverage аналіз
   - 🐳 Docker build та push (на tag)
   - 🚀 Production deploy (manually triggered)

---

## Secrets Management

### Локальні Secrets

```bash
# Ніколи не коммітте .env з реальними ключами!
cp .env.example .env
echo ".env" >> .gitignore
```

### Production Secrets

**Варіант 1: Docker secrets (для Swarm)**
```bash
echo "gsk_your_key" | docker secret create groq_api_key -
docker-compose.yml:
  environment:
    API_KEY_FILE: /run/secrets/groq_api_key
```

**Варіант 2: Environment file**
```bash
# На сервері
echo "API_KEY=gsk_..." > /opt/llm-api/.env.production
chmod 600 /opt/llm-api/.env.production

# docker-compose.yml
env_file:
  - .env.production
```

**Варіант 3: AWS Secrets Manager / HashiCorp Vault**
```bash
# Встановіть клієнт та отримайте secrets перед запуском
aws secretsmanager get-secret-value --secret-id llm-api-secrets
```

### HTTPS/SSL сертифікати

**Let's Encrypt з Certbot:**
```bash
sudo certbot certonly --standalone -d api.yourdomain.com
sudo cp /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem ./cert.pem
sudo cp /etc/letsencrypt/live/api.yourdomain.com/privkey.pem ./key.pem
```

---

## Моніторинг та логування

### Перегляд логів

```bash
# API логи
docker-compose logs -f api

# Nginx логи
docker-compose logs -f nginx

# Redis логи
docker-compose logs -f redis

# Все разом
docker-compose logs -f
```

### Метрики і Моніторинг

Додайте до production docker-compose.yml:

```yaml
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
```

### Health Checks

Endpoint `/health` повертає:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0"
}
```

Проверяйте регулярно:
```bash
# Від сервера
while true; do 
  curl -s http://localhost/health | jq .
  sleep 60
done
```

---

## Автоматичні оновлення

### Через GitHub Actions

1. Зробіть зміни в коді
2. Push до develop
3. Створіть Pull Request
4. Merge до main після затвердження
5. Créate new release tag (v1.0.1)
6. CI/CD автоматично:
   - Запускає тести
   - Будує Docker image
   - Пушить до реєстру
   - (Опціонально) розгортає на production

### Ручне оновлення

```bash
cd /opt/llm-api
git pull origin main
docker-compose -f docker-compose.yml down
docker-compose -f docker-compose.yml pull
docker-compose -f docker-compose.yml up -d
```

---

## Troubleshooting

### Проблема: API не響дає

```bash
# 1. Перевірте контейнер
docker-compose ps

# 2. Перевірте логи
docker-compose logs api

# 3. Перевірте порти
netstat -tulpn | grep 8000

# 4. Перезапустіть
docker-compose restart api
```

### Проблема: Out of memory

```bash
# Перевірте використання
docker stats

# Збільшіть в docker-compose.yml
services:
  api:
    deploy:
      resources:
        limits:
          memory: 4G
```

### Проблема: Nginx 502 Bad Gateway

```bash
# Перевірте що API контейнер запущений
docker-compose logs api

# Перевірте nginx конфіг
docker-compose exec nginx nginx -t

# Перезапустіть nginx
docker-compose restart nginx
```

---

## Резервні копії та відновлення

```bash
# Резервна копія Redis data
docker cp llm-api-redis-1:/data/dump.rdb ./backup/redis-$(date +%Y%m%d).rdb

# Відновлення
docker cp ./backup/redis-20240115.rdb llm-api-redis-1:/data/dump.rdb
docker-compose restart redis
```

---

## Безпека

### Рекомендації

- ✅ Завжди використовуйте HTTPS в production
- ✅ Регулярно оновлюйте залежності: `poetry update`
- ✅ Використовуйте non-root користувача (вже налаштовано)
- ✅ Обмежуйте доступ до API через firewall
- ✅ Ротуйте секрети регулярно
- ✅ Моніторьте логи на аномалії

### Firewall правила

```bash
# Дозволити тільки HTTPS та SSH
sudo ufw default deny incoming
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

---

## Подальші кроки

1. [Встановіть SSL сертифікат](#httpssll-сертифікати)
2. [Налаштуйте моніторинг](#метрики-і-моніторинг)
3. [Додайте authentication](#optional-authentication)
4. [Налаштуйте CI/CD](#cicd-pipeline)

Питання? Відкрийте Issue на GitHub!
