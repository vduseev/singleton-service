# Web Server Example

This example demonstrates a complete web application using **singleton-service** with FastAPI. It showcases middleware integration, dependency injection, and service-oriented architecture.

## 🎯 What You'll Learn

- FastAPI integration with singleton services
- Middleware and dependency injection patterns
- Request/response handling
- Error handling and logging
- API documentation generation

## 📋 Complete Implementation

### Dependencies

```bash
pip install singleton-service fastapi uvicorn pydantic[email] python-multipart
```

### Web Application Service

```python
# services/web_app.py
import logging
from typing import ClassVar, Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import time
from singleton_service import BaseService, requires, guarded
from .config import ConfigService
from .auth import AuthService
from .user_service import UserService

@requires(ConfigService, AuthService, UserService)
class WebAppService(BaseService):
    """FastAPI web application service."""
    
    _app: ClassVar[Optional[FastAPI]] = None
    _request_stats: ClassVar[Dict[str, int]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize FastAPI application with middleware and routes."""
        cls._app = FastAPI(
            title="Singleton Service Web API",
            description="Example web application using singleton-service",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        
        cls._request_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "auth_requests": 0
        }
        
        # Setup middleware
        cls._setup_middleware()
        
        # Setup routes
        cls._setup_routes()
        
        # Setup error handlers
        cls._setup_error_handlers()
    
    @classmethod
    def _setup_middleware(cls) -> None:
        """Configure middleware stack."""
        config = ConfigService.get_config()
        
        # CORS middleware
        cls._app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Trusted host middleware
        cls._app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=config.allowed_hosts
        )
        
        # Custom request logging middleware
        @cls._app.middleware("http")
        async def log_requests(request: Request, call_next):
            start_time = time.time()
            cls._request_stats["total_requests"] += 1
            
            # Process request
            try:
                response = await call_next(request)
                cls._request_stats["successful_requests"] += 1
                
                # Log request
                process_time = time.time() - start_time
                logging.info(
                    f"{request.method} {request.url.path} "
                    f"completed in {process_time:.3f}s with status {response.status_code}"
                )
                
                response.headers["X-Process-Time"] = str(process_time)
                return response
                
            except Exception as e:
                cls._request_stats["failed_requests"] += 1
                logging.error(f"Request failed: {e}")
                raise
    
    @classmethod
    def _setup_routes(cls) -> None:
        """Setup API routes."""
        from .api.auth_routes import router as auth_router
        from .api.user_routes import router as user_router
        from .api.admin_routes import router as admin_router
        
        # Include route modules
        cls._app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
        cls._app.include_router(user_router, prefix="/api/users", tags=["Users"])
        cls._app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])
        
        # Health check endpoint
        @cls._app.get("/health", tags=["Health"])
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "timestamp": time.time(),
                "services": cls._check_service_health()
            }
        
        # Stats endpoint
        @cls._app.get("/stats", tags=["Monitoring"])
        async def get_stats():
            """Get application statistics."""
            return {
                "request_stats": cls._request_stats,
                "service_stats": {
                    "auth": AuthService.get_security_stats(),
                    "users": UserService.get_user_stats()
                }
            }
    
    @classmethod
    def _setup_error_handlers(cls) -> None:
        """Setup custom error handlers."""
        
        @cls._app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException):
            """Handle HTTP exceptions."""
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": exc.detail,
                    "status_code": exc.status_code,
                    "path": str(request.url.path)
                }
            )
        
        @cls._app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            """Handle general exceptions."""
            logging.exception("Unhandled exception occurred")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "status_code": 500,
                    "path": str(request.url.path)
                }
            )
    
    @classmethod
    def _check_service_health(cls) -> Dict[str, str]:
        """Check health of all services."""
        services_health = {}
        
        try:
            services_health["auth"] = "healthy" if AuthService.ping() else "unhealthy"
        except Exception:
            services_health["auth"] = "error"
        
        try:
            services_health["users"] = "healthy" if UserService.ping() else "unhealthy"
        except Exception:
            services_health["users"] = "error"
        
        return services_health
    
    @classmethod
    @guarded
    def get_app(cls) -> FastAPI:
        """Get the FastAPI application instance."""
        return cls._app
    
    @classmethod
    @guarded
    def get_request_stats(cls) -> Dict[str, int]:
        """Get request statistics."""
        return cls._request_stats.copy()
```

### API Routes

```python
# api/auth_routes.py
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from services.auth import AuthService
from services.user_service import UserService

router = APIRouter()
security = HTTPBearer()

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token: str
    user: dict

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """User login endpoint."""
    try:
        # Get user from database
        user = UserService.get_user_by_username(request.username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Authenticate user
        auth_user = AuthService.authenticate(
            username=request.username,
            password=request.password,
            password_hash=user.password_hash,
            user_data={
                "id": user.id,
                "email": user.email,
                "roles": user.roles
            }
        )
        
        return LoginResponse(
            token=auth_user.token,
            user={
                "id": auth_user.user_id,
                "username": auth_user.username,
                "email": auth_user.email,
                "roles": auth_user.roles
            }
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

# api/user_routes.py
from fastapi import APIRouter, HTTPException, Depends, status
from services.user_service import UserService
from models.user import CreateUserRequest, UserResponse

router = APIRouter()

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(request: CreateUserRequest):
    """Create a new user."""
    try:
        return UserService.create_user(request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int):
    """Get user by ID."""
    user = UserService.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
```

### Application Runner

```python
# app.py
import os
import uvicorn
import logging
from dotenv import load_dotenv
from services.web_app import WebAppService

def setup_logging():
    """Configure application logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('app.log')
        ]
    )

def main():
    """Main application entry point."""
    # Load environment variables
    load_dotenv()
    
    # Setup logging
    setup_logging()
    
    # Set required environment variables
    os.environ.setdefault("JWT_SECRET_KEY", "your-secret-key-here")
    os.environ.setdefault("DATABASE_URL", "sqlite:///./app.db")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    
    try:
        # Get FastAPI app from service
        app = WebAppService.get_app()
        
        # Run the application
        uvicorn.run(
            app,
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
            reload=os.getenv("RELOAD", "false").lower() == "true",
            access_log=True
        )
        
    except Exception as e:
        logging.error(f"Failed to start application: {e}")
        raise

if __name__ == "__main__":
    main()
```

## 🚀 Usage Examples

### Running the Application

```bash
# Install dependencies
pip install singleton-service fastapi uvicorn

# Set environment variables
export JWT_SECRET_KEY="your-super-secret-key"
export DATABASE_URL="postgresql://user:pass@localhost/db"

# Run the application
python app.py
```

### API Usage

```bash
# Create a user
curl -X POST "http://localhost:8000/api/users/" \
     -H "Content-Type: application/json" \
     -d '{
       "username": "john_doe",
       "email": "john@example.com",
       "password": "SecurePass123!",
       "first_name": "John",
       "last_name": "Doe"
     }'

# Login
curl -X POST "http://localhost:8000/api/auth/login" \
     -H "Content-Type: application/json" \
     -d '{
       "username": "john_doe",
       "password": "SecurePass123!"
     }'

# Check health
curl "http://localhost:8000/health"

# View API documentation
# Open http://localhost:8000/docs in browser
```

## 🎯 Key Patterns Demonstrated

### 1. FastAPI Integration
- Service-based application architecture
- Dependency injection with singleton services
- Automatic API documentation generation
- Request/response validation

### 2. Middleware Stack
- CORS handling
- Request logging and timing
- Error handling middleware
- Security middleware

### 3. Route Organization
- Modular route definitions
- Service integration in routes
- Proper HTTP status codes
- Consistent error responses

### 4. Health Monitoring
- Service health checks
- Request statistics
- Performance monitoring
- System status endpoints

This example demonstrates a production-ready web application architecture using singleton services with FastAPI.

---

**Next Example**: Learn CLI patterns → [CLI Application](cli-application.md)