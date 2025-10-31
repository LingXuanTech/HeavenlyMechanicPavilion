# Authentication and Authorization Guide

This document provides a comprehensive guide to the authentication and authorization system in TradingAgents.

## Overview

The TradingAgents backend implements a robust authentication and authorization system with the following features:

- **JWT-based user authentication** with access and refresh tokens
- **API key authentication** for service-to-service integrations
- **Role-Based Access Control (RBAC)** with three roles: Admin, Trader, and Viewer
- **Rate limiting** per user/API key using Redis
- **Audit logging** for sensitive operations
- **Password hashing** using bcrypt

## User Roles

### Admin
- Full access to all system features
- User management (create, update, delete users)
- View all audit logs
- Configure vendors and agents
- Execute trades and manage portfolios

### Trader
- Execute trades and manage portfolios
- View own portfolio and positions
- Configure agents
- Create and manage API keys
- View own audit logs

### Viewer
- Read-only access to portfolios and positions
- View market data and analytics
- No ability to execute trades or modify configurations
- Create and manage API keys
- View own audit logs

## Setup

### 1. Configure Environment Variables

Add the following to your `.env` file:

```bash
# Authentication settings
JWT_SECRET_KEY=your-secret-key-here  # Generate with: openssl rand -hex 32
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Rate limiting settings
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# Encryption key for sensitive data
ENCRYPTION_KEY=your-encryption-key-here  # Generate with: openssl rand -base64 32
```

### 2. Run Database Migrations

Apply the authentication tables migration:

```bash
cd packages/backend
.venv/bin/alembic upgrade head
```

### 3. Create Initial Admin User

Create an admin user to get started:

```bash
cd packages/backend
python scripts/create_admin_user.py --username admin --email admin@example.com --password your-secure-password
```

## API Endpoints

### User Registration

**POST** `/auth/register`

Register a new user account.

Request:
```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "securepassword123",
  "full_name": "John Doe",
  "role": "viewer"
}
```

Response:
```json
{
  "id": 1,
  "username": "johndoe",
  "email": "john@example.com",
  "full_name": "John Doe",
  "role": "viewer",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2024-01-15T10:00:00Z",
  "last_login_at": null
}
```

### User Login

**POST** `/auth/login`

Login and receive JWT tokens.

Request:
```json
{
  "username": "johndoe",
  "password": "securepassword123"
}
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Get Current User

**GET** `/auth/me`

Get current authenticated user information.

Headers:
```
Authorization: Bearer <access_token>
```

Response:
```json
{
  "id": 1,
  "username": "johndoe",
  "email": "john@example.com",
  "full_name": "John Doe",
  "role": "trader",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2024-01-15T10:00:00Z",
  "last_login_at": "2024-01-15T12:00:00Z"
}
```

### Refresh Token

**POST** `/auth/refresh`

Refresh access token using refresh token.

Request:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Change Password

**POST** `/auth/change-password`

Change current user's password.

Headers:
```
Authorization: Bearer <access_token>
```

Request:
```json
{
  "old_password": "oldpassword",
  "new_password": "newsecurepassword123"
}
```

### Create API Key

**POST** `/auth/api-keys`

Create a new API key for service-to-service authentication.

Headers:
```
Authorization: Bearer <access_token>
```

Request:
```json
{
  "name": "Production API Key",
  "expires_at": "2025-01-15T00:00:00Z"
}
```

Response:
```json
{
  "id": 1,
  "name": "Production API Key",
  "key": "ta_abc123def456...",
  "created_at": "2024-01-15T10:00:00Z",
  "expires_at": "2025-01-15T00:00:00Z",
  "last_used_at": null,
  "is_active": true
}
```

**⚠️ Important:** The plain API key is only returned once during creation. Store it securely!

### List API Keys

**GET** `/auth/api-keys`

List all API keys for the current user.

Headers:
```
Authorization: Bearer <access_token>
```

### Revoke API Key

**DELETE** `/auth/api-keys/{key_id}`

Revoke an API key.

Headers:
```
Authorization: Bearer <access_token>
```

### Admin Endpoints

#### List Users

**GET** `/auth/users`

List all users (Admin only).

Headers:
```
Authorization: Bearer <access_token>
```

#### Update User

**PUT** `/auth/users/{user_id}`

Update a user (Admin only).

Headers:
```
Authorization: Bearer <access_token>
```

Request:
```json
{
  "email": "newemail@example.com",
  "full_name": "Updated Name",
  "role": "trader",
  "is_active": true
}
```

#### Delete User

**DELETE** `/auth/users/{user_id}`

Delete a user (Admin only).

Headers:
```
Authorization: Bearer <access_token>
```

### Audit Logs

#### List All Audit Logs

**GET** `/auth/audit-logs?limit=100`

List audit logs (Admin only).

Headers:
```
Authorization: Bearer <access_token>
```

#### List My Audit Logs

**GET** `/auth/audit-logs/me?limit=50`

List current user's audit logs.

Headers:
```
Authorization: Bearer <access_token>
```

## Authentication Methods

### 1. JWT Bearer Token

Include the access token in the Authorization header:

```bash
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  http://localhost:8000/auth/me
```

### 2. API Key

Include the API key in the X-API-Key header:

```bash
curl -H "X-API-Key: ta_abc123def456..." \
  http://localhost:8000/trading/portfolio
```

## Rate Limiting

Rate limiting is enforced per user/API key and per IP address:

- **Per User/API Key:**
  - 60 requests per minute
  - 1000 requests per hour

- **Per IP Address:**
  - 120 requests per minute (unauthenticated)

Rate limits are configurable via environment variables:

```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000
```

When rate limit is exceeded, the API returns a `429 Too Many Requests` response with a `Retry-After` header.

## Protecting Routes

### Using Dependencies

Protect routes using FastAPI dependencies:

```python
from fastapi import APIRouter, Depends
from app.security import get_current_active_user, require_role
from app.db.models import User, UserRole

router = APIRouter()

# Require authentication
@router.get("/protected")
async def protected_route(
    current_user: User = Depends(get_current_active_user)
):
    return {"message": f"Hello {current_user.username}"}

# Require specific role
@router.post("/admin-only")
async def admin_only_route(
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    return {"message": "Admin access granted"}

# Require one of multiple roles
@router.post("/trader-or-admin")
async def trader_or_admin_route(
    current_user: User = Depends(require_role(UserRole.TRADER, UserRole.ADMIN))
):
    return {"message": "Trader or admin access granted"}
```

### Optional Authentication

For routes that work with or without authentication:

```python
from app.security import get_optional_user

@router.get("/optional-auth")
async def optional_auth_route(
    current_user: Optional[User] = Depends(get_optional_user)
):
    if current_user:
        return {"message": f"Hello {current_user.username}"}
    return {"message": "Hello anonymous user"}
```

## Audit Logging

All sensitive operations are automatically logged:

- User registration, login, and logout
- Password changes
- API key creation and revocation
- User updates and deletions (admin)
- Configuration changes

Audit logs include:
- User ID
- Action performed
- Resource type and ID
- IP address
- User agent
- Timestamp
- Status (success/failure)

## Security Best Practices

1. **Strong JWT Secret:** Use a strong, randomly generated secret key
   ```bash
   openssl rand -hex 32
   ```

2. **Secure Password Policy:** Enforce minimum password length (8+ characters)

3. **Token Expiration:** 
   - Access tokens: 30 minutes (short-lived)
   - Refresh tokens: 7 days

4. **HTTPS Only:** Always use HTTPS in production

5. **Rate Limiting:** Enable rate limiting to prevent brute-force attacks

6. **API Key Rotation:** Regularly rotate API keys

7. **Audit Logs:** Regularly review audit logs for suspicious activity

8. **Environment Variables:** Never commit secrets to version control

## Example Usage

### Python Client

```python
import httpx

class TradingAgentsClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.access_token = None
        self.refresh_token = None
    
    async def login(self, username: str, password: str):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/auth/login",
                json={"username": username, "password": password}
            )
            response.raise_for_status()
            data = response.json()
            self.access_token = data["access_token"]
            self.refresh_token = data["refresh_token"]
    
    async def get_portfolio(self):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/trading/portfolio",
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            response.raise_for_status()
            return response.json()

# Usage
client = TradingAgentsClient("http://localhost:8000")
await client.login("trader", "password123")
portfolio = await client.get_portfolio()
```

### JavaScript/TypeScript Client

```typescript
class TradingAgentsClient {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;

  constructor(private baseUrl: string) {}

  async login(username: string, password: string) {
    const response = await fetch(`${this.baseUrl}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    
    if (!response.ok) {
      throw new Error('Login failed');
    }
    
    const data = await response.json();
    this.accessToken = data.access_token;
    this.refreshToken = data.refresh_token;
  }

  async getPortfolio() {
    const response = await fetch(`${this.baseUrl}/trading/portfolio`, {
      headers: {
        'Authorization': `Bearer ${this.accessToken}`,
      },
    });
    
    if (!response.ok) {
      throw new Error('Failed to fetch portfolio');
    }
    
    return await response.json();
  }
}

// Usage
const client = new TradingAgentsClient('http://localhost:8000');
await client.login('trader', 'password123');
const portfolio = await client.getPortfolio();
```

## Troubleshooting

### "Not authenticated" error
- Ensure you're including the `Authorization` header with a valid token
- Check if the token has expired (access tokens expire after 30 minutes)
- Try refreshing the token using the `/auth/refresh` endpoint

### "Insufficient permissions" error
- Verify your user role has access to the endpoint
- Admin-only endpoints require `UserRole.ADMIN`
- Contact an administrator to update your role if needed

### Rate limit exceeded
- Wait for the rate limit window to reset
- Implement exponential backoff in your client
- Consider using API keys for service-to-service calls

### Invalid credentials
- Verify username and password are correct
- Check if the user account is active
- Contact an administrator if account is locked

## Migration Guide

For existing deployments, follow these steps to add authentication:

1. **Backup your database**
2. **Update dependencies:**
   ```bash
   cd packages/backend
   pip install bcrypt python-jose[cryptography] python-multipart
   ```
3. **Run migrations:**
   ```bash
   .venv/bin/alembic upgrade head
   ```
4. **Create admin user:**
   ```bash
   python scripts/create_admin_user.py
   ```
5. **Update your client applications** to use authentication
6. **Update environment variables** with JWT and encryption keys

## Support

For questions or issues with authentication, please:
- Check the API documentation at `/docs`
- Review audit logs for error details
- Contact your system administrator
