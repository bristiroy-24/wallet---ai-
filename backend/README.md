# WalletAI Backend – FastAPI + PostgreSQL + Gemini AI

Production-ready REST API for the WalletAI Expense Tracker.

## Quick Start (Local)

### Prerequisites
- Python 3.12+
- PostgreSQL 15+ running locally (or use Docker Compose)

### 1. Set up environment
```bash
cd backend
cp .env.example .env
# Edit .env: set DATABASE_URL, GEMINI_API_KEY, SECRET_KEY
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run database migrations
```bash
alembic upgrade head
```

### 4. Start the server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Visit **http://localhost:8000/docs** for the interactive Swagger UI.

---

## Docker Compose (Recommended)

Starts PostgreSQL + FastAPI together:
```bash
docker-compose up --build
```

---

## Enabling Real Gemini AI

1. Get your API key at https://makersuite.google.com/app/apikey
2. In `.env`:
   ```
   GEMINI_API_KEY=your-real-key-here
   USE_REAL_AI=true
   ```
3. Restart the server.

---

## Project Structure

```
backend/
├── app/
│   ├── core/
│   │   ├── config.py         # pydantic-settings – all env vars
│   │   ├── security.py       # JWT + bcrypt helpers
│   │   ├── exceptions.py     # Domain exception hierarchy
│   │   └── dependencies.py   # FastAPI DI (DB session, auth, AI)
│   ├── db/
│   │   ├── base.py           # Declarative base + model imports
│   │   ├── session.py        # Async engine + session factory
│   │   └── seed.py           # Default category seeder
│   ├── models/               # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── account.py
│   │   ├── category.py
│   │   ├── transaction.py
│   │   └── ai_insight.py
│   ├── schemas/              # Pydantic v2 DTOs
│   │   ├── user.py
│   │   ├── account.py
│   │   ├── category.py
│   │   ├── transaction.py
│   │   └── ai.py             # ParsedExpenseSchema, InsightSchema, DashboardSchema
│   ├── repositories/         # Data Access Layer (Repository Pattern)
│   │   ├── base.py           # Generic BaseRepository[T]
│   │   ├── user.py
│   │   ├── account.py
│   │   ├── category.py
│   │   ├── transaction.py    # Rich filtered queries + analytics
│   │   └── insight.py
│   ├── services/             # Business Logic Layer
│   │   ├── ai_base.py        # BaseAIService (Strategy interface)
│   │   ├── gemini_service.py # GeminiAIService (google-genai SDK)
│   │   ├── mock_ai_service.py# MockAIService (no-network testing)
│   │   ├── ai_factory.py     # AIFactory (Factory Pattern)
│   │   └── analytics_service.py
│   ├── routers/              # FastAPI route handlers
│   │   ├── auth.py           # POST /auth/register, /auth/login
│   │   ├── accounts.py       # CRUD /api/v1/accounts
│   │   ├── categories.py     # GET /api/v1/categories
│   │   ├── transactions.py   # CRUD + /magic-input + /scan-receipt
│   │   └── analytics.py      # /dashboard + /insights
│   └── main.py               # App factory, CORS, global handlers
├── alembic/                  # Database migrations
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Get JWT token |
| GET  | `/api/v1/accounts` | List accounts |
| POST | `/api/v1/accounts` | Add account |
| GET  | `/api/v1/categories` | Category tree |
| GET  | `/api/v1/transactions` | Filtered transactions |
| POST | `/api/v1/transactions` | Create transaction |
| POST | `/api/v1/transactions/magic-input` | AI NLP parse |
| POST | `/api/v1/transactions/scan-receipt` | AI OCR receipt |
| GET  | `/api/v1/analytics/dashboard` | Dashboard stats |
| GET  | `/api/v1/analytics/insights` | AI insights |
| POST | `/api/v1/analytics/insights/refresh` | Regenerate AI insights |

---

## Design Patterns Used

| Pattern | Where | Why |
|---------|-------|-----|
| Repository | `repositories/` | Decouples data access from business logic |
| Strategy | `services/ai_base.py` | Swap AI providers without touching routers |
| Factory | `services/ai_factory.py` | Selects the right Strategy at runtime |
| Dependency Injection | `core/dependencies.py` | FastAPI DI for DB, auth, AI service |
| DTO / Schema | `schemas/` | Clean API contracts, no ORM leakage |
