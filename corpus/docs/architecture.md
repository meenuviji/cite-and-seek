# Ecommerce Microservice API — Architecture & Configuration
(Source: extracted verbatim from the upstream repository's README.md — Franklindot04/ecommerce-api, MIT licensed)

## Features

### Products API
- Create products.
- Retrieve all products.
- Retrieve a single product.
- Pydantic validation.
- Seeded demo inventory.
- Redis-backed caching for product list and product detail retrieval.

### Shopping Cart API
- Add products to cart.
- Merge duplicate cart items.
- View cart contents.
- Remove individual items.
- Clear entire cart.
- Validate stock availability.

### Orders API
- Checkout cart items.
- Validate stock during checkout.
- Create order records and order items.
- Persist order history.
- Decrement inventory.
- Clear cart after purchase.
- Retrieve all orders.
- Retrieve individual orders.
- Nested serialization using eager loading.
- Cache invalidation after inventory-changing operations.

### Order Lifecycle API
- Order status support.
- Status transitions.
- Order cancellation rules.
- State-machine style workflow validation.
- Swagger-visible status fields.

### Payments API
- Mock payment creation for orders.
- Payment amount tracking.
- Payment provider tracking.
- Payment status tracking.
- Payment-to-user association.
- Payment-to-order association.
- Order-aware mock payment workflow.
- Database-backed payment persistence.
- Alembic-managed payments schema evolution.

### Background Tasks
- Invoice generation after checkout.
- Order-created notification generation.
- Order-status-updated notification generation.
- Order-cancelled notification generation.
- FastAPI `BackgroundTasks` integration for deferred side effects.
- Local file-based background task outputs for invoices and notifications.
- Timezone-aware UTC timestamps for generated artifacts.

### Authentication API
- User registration.
- User login.
- JWT access tokens.
- Password hashing with bcrypt.
- Protected user route.
- Swagger OAuth2 password flow.
- Redis-backed login rate limiting.

### Multi-user Ecommerce API
- User-owned cart items.
- User-owned orders.
- User-scoped cart access.
- User-scoped order access.
- Per-user checkout flow.
- Ownership protection for order retrieval and updates.
- Protected cart and order endpoints.

### Database Migration Support
- Alembic integration for schema migrations.
- Initial baseline migration.
- SQLite-compatible migration configuration.
- Database revision tracking with `alembic_version`.
- Version-controlled schema evolution for future changes.
- Payments table migration added and verified.

### Testing
- Pytest-based automated test suite.
- Shared fixtures with `conftest.py`.
- Isolated SQLite test database.
- FastAPI dependency overrides for test isolation.
- In-memory `FakeRedis` test client for cache and rate-limit isolation.
- Auth, products, cart, orders, and payments endpoint coverage.
- Background task side-effect coverage for invoices and notifications.

## Configuration

Copy the example environment file and adjust values as needed:

```bash
cp .env.example .env
```

Current configurable settings include:
- `DATABASE_URL`
- `SECRET_KEY`
- `ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `APP_HOST`
- `APP_PORT`
- `REDIS_URL`
- `PRODUCT_CACHE_TTL`
- `RATE_LIMIT_TIMES`
- `RATE_LIMIT_SECONDS`

Notes:
- `.env.example` is committed as a safe template.
- `.env` remains local and should not be committed.
- Application settings are centralized in `app/config.py`.

## Running Migrations

Create or update the local database schema with:

```bash
alembic upgrade head
```

Current migration baseline:
- Initial schema migration: `6f5e3d5e8133`
- Payments migration: `14051421d3f0`
- Verified local database head: `14051421d3f0 (head)`
- Verified `payments` table present in SQLite after upgrade

## Current Architecture

```text
app/
├── api/                    # API route handlers
│   ├── auth.py             # Authentication endpoints
│   ├── products.py         # Product endpoints with caching
│   ├── cart.py             # User-scoped cart endpoints
│   ├── orders.py           # User-scoped order endpoints with background tasks
│   └── payments.py         # Mock payment endpoints
├── services/               # Business logic and supporting workflows
│   ├── cart_service.py     # Cart business logic
│   ├── invoice_service.py  # Invoice file generation
│   ├── notification_service.py # Order notification file generation
│   ├── order_service.py    # Order business logic
│   └── payment_service.py  # Mock payment workflow logic
├── auth_utils.py           # Password hashing, JWT, auth dependency
├── cache_utils.py          # Cache invalidation helpers
├── config.py               # Centralized application settings
├── models.py                # SQLAlchemy models, including Payment
├── rate_limiter.py          # Login rate limiting dependency
└── schemas.py                # Pydantic schemas
```

The router modularization was introduced after Stage 4, the service layer was added
in Stage 8, Alembic migration support was added in Stage 9, automated testing
support was added in Stage 10, Redis-backed caching and rate limiting were added
in Stage 12, background task support for invoices and notifications was added in
Stage 13, and mock payment support was added in Stage 14.

## Tech Stack

Python, FastAPI, SQLite, SQLAlchemy, Alembic, Redis, Pydantic, Pydantic-Settings,
JWT, OAuth2 password flow, bcrypt password hashing, Swagger/OpenAPI, service-layer
architecture, Pytest, HTTPX, Docker, Docker Compose.
