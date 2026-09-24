# POS API

A secure **Point-of-Sale backend** built with **FastAPI, SQLAlchemy, and PostgreSQL**, featuring JWT authentication, role-based access control, input validation, brute-force protection, and automated tests.

## Features

* JWT bearer authentication
* Role-based access control
* Admin, manager, and cashier roles
* Argon2id password hashing
* Login brute-force protection
* PostgreSQL support
* SQLite support for testing
* Input validation and pagination
* Security headers and CORS configuration
* Production security settings
* Automated test suite
* Swagger/OpenAPI documentation in development

## Tech Stack

| Technology | Purpose                 |
| ---------- | ----------------------- |
| FastAPI    | REST API framework      |
| SQLAlchemy | ORM and database access |
| PostgreSQL | Production database     |
| SQLite     | Default test database   |
| JWT        | Authentication          |
| Argon2id   | Password hashing        |
| Pytest     | Testing                 |

## Project Setup

### 1. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate
```

Windows:

```bash
venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

For development and testing:

```bash
pip install -r requirements-dev.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Generate a secure secret key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Add the generated value to `.env` as `SECRET_KEY`.

The application requires:

* `DATABASE_URL`
* `SECRET_KEY` with at least 32 bytes
* A non-placeholder secret key

The application refuses to start if these required settings are missing or invalid.

### 4. Initialize the database

```bash
python init_db.py
```

Tables are also created automatically when the application starts.

### 5. Create the first admin

```bash
python create_admin.py
```

The command prompts for the administrator credentials. Public admin registration is not available.

### 6. Start the API

```bash
uvicorn app.main:app --reload
```

API:

```text
http://127.0.0.1:8000
```

Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

## Authentication

Login uses form-encoded credentials.

```bash
curl -d "username=admin&password=YOUR_PASSWORD" \
  http://127.0.0.1:8000/auth/login
```

Response:

```json
{
  "access_token": "YOUR_TOKEN",
  "token_type": "bearer"
}
```

Use the token for protected requests:

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://127.0.0.1:8000/products/
```

### Authentication Endpoints

| Method | Endpoint                | Description                        |
| ------ | ----------------------- | ---------------------------------- |
| POST   | `/auth/login`           | Authenticate and receive a JWT     |
| GET    | `/auth/me`              | Get the authenticated user         |
| POST   | `/auth/change-password` | Change the current user's password |

Access tokens expire after **30 minutes** by default.

Changing a password invalidates older tokens immediately.

## Roles & Permissions

| Resource                                      | Admin | Manager | Cashier |
| --------------------------------------------- | :---: | :-----: | :-----: |
| Users                                         |   ✓   |    —    |    —    |
| Suppliers                                     |   ✓   |    ✓    |    —    |
| Categories — read                             |   ✓   |    ✓    |    ✓    |
| Categories — write                            |   ✓   |    ✓    |    —    |
| Products — read                               |   ✓   |    ✓    |    ✓    |
| Products — write                              |   ✓   |    ✓    |    —    |
| Inventory — read                              |   ✓   |    ✓    |    ✓    |
| Inventory — write                             |   ✓   |    ✓    |    —    |
| Customers — read/create/update                |   ✓   |    ✓    |    ✓    |
| Customers — delete                            |   ✓   |    ✓    |    —    |
| Sales — read/create                           |   ✓   |    ✓    |    ✓    |
| Sale items — read/create                      |   ✓   |    ✓    |    ✓    |
| Payments — read/create                        |   ✓   |    ✓    |    ✓    |
| Receipts — read/create                        |   ✓   |    ✓    |    ✓    |
| Sales/items/payments/receipts — update/delete |   ✓   |    ✓    |    —    |

### Cashier Restrictions

Cashiers:

* Can only create sales for themselves.
* Can only add items, payments, and receipts to their own sales.
* Can only access their own sales.
* Cannot view `medical_conditions`.
* Cannot set or modify `medical_conditions`.

The system always maintains at least one active administrator. The final active admin cannot be deleted, demoted, or deactivated.

## Security

### Password Protection

Passwords are protected using **Argon2id**.

Password requirements:

* 12–128 characters
* At least one letter
* At least one digit

Password hashes are never accepted from or returned to API clients.

Existing password hashes can be automatically upgraded when hashing parameters change.

### JWT Security

Tokens use signed JWTs with:

* Pinned signing algorithm
* `exp`
* `iat`
* `sub`

Tokens are checked against the database on every request.

This means changes to:

* User activation status
* User role
* Password

take effect immediately.

### Brute-Force Protection

Login attempts are limited to:

**5 failed attempts per username + IP address**

After the limit is reached, the account/IP combination is locked for **5 minutes** and returns `429`.

Unknown usernames use the same authentication work and return the same error message as invalid passwords to reduce username enumeration.

### API Protection

The API follows a **default-deny** security model.

Protected routers require a valid authenticated user.

Additional protections include:

* Request validation
* Bounded IDs
* Positive quantities
* Non-negative monetary values
* Correct monetary precision
* Maximum pagination limit of 500
* PATCH validation that prevents required fields from becoming `NULL`
* Clean `409` responses for database constraint violations
* Server-side error logging
* Security headers
* Configurable CORS

## Pagination

List endpoints support:

```text
?skip=0&limit=100
```

The maximum allowed limit is:

```text
500
```

Example:

```bash
GET /products/?skip=0&limit=50
```

## Production Security

Set:

```env
ENVIRONMENT=production
```

Before deployment:

1. Generate a fresh random `SECRET_KEY`.
2. Use HTTPS.
3. Use `?sslmode=require` for remote PostgreSQL databases.
4. Configure the reverse proxy to forward the real client IP.
5. Run Uvicorn with appropriate proxy settings.
6. Use a shared rate limiter such as Redis when running multiple workers or containers.
7. Use a least-privilege PostgreSQL user.
8. Keep database schema management separate from the application database user when appropriate.
9. Use Alembic for future schema migrations.
10. Keep `/docs` and `/openapi.json` disabled in production.

Example:

```bash
uvicorn app.main:app \
  --proxy-headers \
  --forwarded-allow-ips=<PROXY_IP>
```

## Testing

The test suite uses SQLite by default.

Run all tests:

```bash
pytest
```

Run tests with coverage:

```bash
pytest --cov=app --cov-report=term-missing
```

Run against PostgreSQL:

```bash
TEST_DATABASE_URL=postgresql+psycopg2://user:pw@localhost:5432/pos_test pytest
```

## Database Notes

No database schema changes were introduced in the current version.

Existing databases remain compatible.

`create_all` creates missing tables but does **not** modify existing tables.

For future schema changes, use **Alembic** migrations.

## Current Behaviour

The following behaviours are intentionally unchanged from the original implementation:

### Sales and Inventory

Sale totals and item totals are supplied by the client.

The backend currently does not:

* Recalculate sale totals
* Reconcile totals with payments
* Automatically decrement inventory when products are sold

### Deletion Rules

Deleting a customer, category, or supplier that is referenced by other records sets the relationship to `NULL` instead of blocking the deletion.

Deleting a user with existing sales is blocked.

Deleting a product with existing sale items or inventory is blocked.

## API Documentation

When running in development:

```text
Swagger UI: http://127.0.0.1:8000/docs
OpenAPI:    http://127.0.0.1:8000/openapi.json
```

Both documentation endpoints are disabled when:

```env
ENVIRONMENT=production
```

## Future Improvements

Potential production enhancements include:

* Refresh tokens
* Token deny-list / logout support
* Redis-based distributed rate limiting
* Alembic migrations
* Server-side sale total calculation
* Payment reconciliation
* Automatic inventory deduction
* Stronger audit logging
* Centralized monitoring and observability


