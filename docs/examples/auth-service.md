# Auth Service Example

This example demonstrates a comprehensive authentication service using **singleton-service**. It showcases JWT token management, session handling, password security, and role-based access control.

## 🎯 What You'll Learn

- JWT token generation and validation
- Session management and storage
- Password hashing and security
- Role-based access control (RBAC)
- Authentication middleware patterns
- Security best practices

## 📋 Complete Implementation

### Dependencies

```bash
pip install singleton-service pyjwt cryptography bcrypt redis python-dotenv
```

### Configuration Service

```python
# services/config.py
import os
from typing import ClassVar, Optional
from dataclasses import dataclass
from singleton_service import BaseService, guarded

@dataclass
class AuthConfig:
    """Type-safe authentication configuration."""
    jwt_secret_key: str
    jwt_algorithm: str
    jwt_expiry_hours: int
    session_expiry_hours: int
    redis_url: str
    password_min_length: int
    max_login_attempts: int
    lockout_duration_minutes: int

class ConfigService(BaseService):
    """Authentication configuration management."""
    
    _config: ClassVar[Optional[AuthConfig]] = None
    
    @classmethod
    def initialize(cls) -> None:
        """Load and validate authentication configuration."""
        # Required settings
        jwt_secret = os.getenv("JWT_SECRET_KEY")
        if not jwt_secret:
            raise ValueError(
                "JWT_SECRET_KEY environment variable is required. "
                "Generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        
        if len(jwt_secret) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long")
        
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        # Optional settings with defaults
        try:
            jwt_expiry = int(os.getenv("JWT_EXPIRY_HOURS", "24"))
            session_expiry = int(os.getenv("SESSION_EXPIRY_HOURS", "168"))  # 1 week
            password_min_length = int(os.getenv("PASSWORD_MIN_LENGTH", "8"))
            max_login_attempts = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
            lockout_duration = int(os.getenv("LOCKOUT_DURATION_MINUTES", "30"))
        except ValueError as e:
            raise ValueError(f"Invalid authentication configuration: {e}")
        
        # Validate ranges
        if jwt_expiry < 1 or jwt_expiry > 168:  # 1 hour to 1 week
            raise ValueError("JWT_EXPIRY_HOURS must be between 1 and 168")
        
        if password_min_length < 6 or password_min_length > 128:
            raise ValueError("PASSWORD_MIN_LENGTH must be between 6 and 128")
        
        cls._config = AuthConfig(
            jwt_secret_key=jwt_secret,
            jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            jwt_expiry_hours=jwt_expiry,
            session_expiry_hours=session_expiry,
            redis_url=redis_url,
            password_min_length=password_min_length,
            max_login_attempts=max_login_attempts,
            lockout_duration_minutes=lockout_duration
        )
    
    @classmethod
    @guarded
    def get_config(cls) -> AuthConfig:
        """Get validated authentication configuration."""
        return cls._config
```

### Session Storage Service

```python
# services/session_storage.py
import json
import redis
from typing import ClassVar, Optional, Dict, Any
from singleton_service import BaseService, requires, guarded
from .config import ConfigService

@requires(ConfigService)
class SessionStorageService(BaseService):
    """Redis-based session storage with expiration."""
    
    _redis_client: ClassVar[Optional[redis.Redis]] = None
    _stats: ClassVar[Dict[str, int]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize Redis connection."""
        config = ConfigService.get_config()
        
        cls._redis_client = redis.from_url(
            config.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True
        )
        
        cls._stats = {
            "sessions_created": 0,
            "sessions_retrieved": 0,
            "sessions_deleted": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        # Test connection
        cls._redis_client.ping()
    
    @classmethod
    def ping(cls) -> bool:
        """Test Redis connectivity."""
        try:
            cls._redis_client.ping()
            return True
        except Exception:
            return False
    
    @classmethod
    @guarded
    def create_session(cls, session_id: str, data: Dict[str, Any], expiry_hours: Optional[int] = None) -> None:
        """Create a new session with expiration."""
        config = ConfigService.get_config()
        expiry = expiry_hours or config.session_expiry_hours
        
        try:
            session_data = json.dumps(data)
            cls._redis_client.setex(
                f"session:{session_id}",
                expiry * 3600,  # Convert hours to seconds
                session_data
            )
            cls._stats["sessions_created"] += 1
            
        except Exception as e:
            raise RuntimeError(f"Failed to create session: {e}")
    
    @classmethod
    @guarded
    def get_session(cls, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data by session ID."""
        try:
            session_data = cls._redis_client.get(f"session:{session_id}")
            cls._stats["sessions_retrieved"] += 1
            
            if session_data:
                cls._stats["cache_hits"] += 1
                return json.loads(session_data)
            else:
                cls._stats["cache_misses"] += 1
                return None
                
        except Exception as e:
            cls._stats["cache_misses"] += 1
            raise RuntimeError(f"Failed to get session: {e}")
    
    @classmethod
    @guarded
    def update_session(cls, session_id: str, data: Dict[str, Any]) -> bool:
        """Update existing session data."""
        try:
            # Get current TTL
            ttl = cls._redis_client.ttl(f"session:{session_id}")
            if ttl <= 0:
                return False  # Session doesn't exist or has expired
            
            # Update with same TTL
            session_data = json.dumps(data)
            cls._redis_client.setex(f"session:{session_id}", ttl, session_data)
            return True
            
        except Exception as e:
            raise RuntimeError(f"Failed to update session: {e}")
    
    @classmethod
    @guarded
    def delete_session(cls, session_id: str) -> bool:
        """Delete a session."""
        try:
            result = cls._redis_client.delete(f"session:{session_id}")
            if result:
                cls._stats["sessions_deleted"] += 1
            return bool(result)
            
        except Exception as e:
            raise RuntimeError(f"Failed to delete session: {e}")
    
    @classmethod
    @guarded
    def extend_session(cls, session_id: str, hours: int) -> bool:
        """Extend session expiration."""
        try:
            result = cls._redis_client.expire(f"session:{session_id}", hours * 3600)
            return bool(result)
            
        except Exception as e:
            raise RuntimeError(f"Failed to extend session: {e}")
    
    @classmethod
    @guarded
    def get_active_sessions_count(cls) -> int:
        """Get count of active sessions."""
        try:
            pattern = "session:*"
            return len(cls._redis_client.keys(pattern))
        except Exception as e:
            raise RuntimeError(f"Failed to count sessions: {e}")
    
    @classmethod
    @guarded
    def cleanup_expired_sessions(cls) -> int:
        """Manually cleanup expired sessions (Redis handles this automatically)."""
        # Redis automatically handles expiration, but we can track it
        try:
            pattern = "session:*"
            all_sessions = cls._redis_client.keys(pattern)
            active_sessions = []
            
            for session_key in all_sessions:
                ttl = cls._redis_client.ttl(session_key)
                if ttl > 0:
                    active_sessions.append(session_key)
            
            expired_count = len(all_sessions) - len(active_sessions)
            return expired_count
            
        except Exception as e:
            raise RuntimeError(f"Failed to cleanup sessions: {e}")
    
    @classmethod
    @guarded
    def get_stats(cls) -> Dict[str, Any]:
        """Get session storage statistics."""
        total_requests = cls._stats["cache_hits"] + cls._stats["cache_misses"]
        hit_rate = cls._stats["cache_hits"] / max(total_requests, 1) * 100
        
        return {
            **cls._stats,
            "active_sessions": cls.get_active_sessions_count(),
            "hit_rate_percent": round(hit_rate, 2),
            "total_requests": total_requests
        }
```

### Password Service

```python
# services/password.py
import bcrypt
import secrets
import string
from typing import ClassVar, Dict, Any
from singleton_service import BaseService, requires, guarded
from .config import ConfigService

@requires(ConfigService)
class PasswordService(BaseService):
    """Secure password hashing and validation service."""
    
    _stats: ClassVar[Dict[str, int]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize password service."""
        cls._stats = {
            "passwords_hashed": 0,
            "passwords_verified": 0,
            "passwords_generated": 0
        }
    
    @classmethod
    @guarded
    def hash_password(cls, password: str) -> str:
        """Hash a password using bcrypt."""
        if not cls._validate_password_strength(password):
            config = ConfigService.get_config()
            raise ValueError(
                f"Password must be at least {config.password_min_length} characters long and contain "
                "uppercase, lowercase, digit, and special character"
            )
        
        try:
            # Generate salt and hash password
            salt = bcrypt.gensalt(rounds=12)
            password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
            
            cls._stats["passwords_hashed"] += 1
            return password_hash.decode('utf-8')
            
        except Exception as e:
            raise RuntimeError(f"Password hashing failed: {e}")
    
    @classmethod
    @guarded
    def verify_password(cls, password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        try:
            result = bcrypt.checkpw(
                password.encode('utf-8'),
                password_hash.encode('utf-8')
            )
            cls._stats["passwords_verified"] += 1
            return result
            
        except Exception as e:
            raise RuntimeError(f"Password verification failed: {e}")
    
    @classmethod
    @guarded
    def generate_secure_password(cls, length: int = 16) -> str:
        """Generate a cryptographically secure random password."""
        if length < 8 or length > 128:
            raise ValueError("Password length must be between 8 and 128")
        
        # Ensure password contains at least one character from each category
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        special = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        
        password = [
            secrets.choice(lowercase),
            secrets.choice(uppercase),
            secrets.choice(digits),
            secrets.choice(special)
        ]
        
        # Fill remaining length with random characters
        all_chars = lowercase + uppercase + digits + special
        for _ in range(length - 4):
            password.append(secrets.choice(all_chars))
        
        # Shuffle the password
        secrets.SystemRandom().shuffle(password)
        
        cls._stats["passwords_generated"] += 1
        return ''.join(password)
    
    @classmethod
    def _validate_password_strength(cls, password: str) -> bool:
        """Validate password meets security requirements."""
        config = ConfigService.get_config()
        
        if len(password) < config.password_min_length:
            return False
        
        # Check for required character types
        has_lower = any(c.islower() for c in password)
        has_upper = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        return has_lower and has_upper and has_digit and has_special
    
    @classmethod
    @guarded
    def check_password_strength(cls, password: str) -> Dict[str, Any]:
        """Check password strength and return detailed analysis."""
        config = ConfigService.get_config()
        
        checks = {
            "length_ok": len(password) >= config.password_min_length,
            "has_lowercase": any(c.islower() for c in password),
            "has_uppercase": any(c.isupper() for c in password),
            "has_digit": any(c.isdigit() for c in password),
            "has_special": any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password),
            "no_common_patterns": not cls._has_common_patterns(password)
        }
        
        score = sum(checks.values())
        strength_levels = {
            6: "Very Strong",
            5: "Strong", 
            4: "Moderate",
            3: "Weak",
            0: "Very Weak"
        }
        
        strength = strength_levels.get(score, "Very Weak")
        
        return {
            "score": score,
            "max_score": 6,
            "strength": strength,
            "is_valid": score >= 5,
            "checks": checks,
            "suggestions": cls._get_password_suggestions(checks)
        }
    
    @classmethod
    def _has_common_patterns(cls, password: str) -> bool:
        """Check for common password patterns."""
        password_lower = password.lower()
        
        # Common patterns to avoid
        common_patterns = [
            "password", "123456", "qwerty", "admin", "login",
            "welcome", "letmein", "monkey", "dragon", "master"
        ]
        
        for pattern in common_patterns:
            if pattern in password_lower:
                return True
        
        # Check for keyboard patterns
        keyboard_patterns = ["qwerty", "asdf", "zxcv", "1234", "abcd"]
        for pattern in keyboard_patterns:
            if pattern in password_lower:
                return True
        
        return False
    
    @classmethod
    def _get_password_suggestions(cls, checks: Dict[str, bool]) -> List[str]:
        """Get suggestions for improving password strength."""
        suggestions = []
        
        if not checks["length_ok"]:
            config = ConfigService.get_config()
            suggestions.append(f"Use at least {config.password_min_length} characters")
        
        if not checks["has_lowercase"]:
            suggestions.append("Include lowercase letters (a-z)")
        
        if not checks["has_uppercase"]:
            suggestions.append("Include uppercase letters (A-Z)")
        
        if not checks["has_digit"]:
            suggestions.append("Include numbers (0-9)")
        
        if not checks["has_special"]:
            suggestions.append("Include special characters (!@#$%^&*)")
        
        if not checks["no_common_patterns"]:
            suggestions.append("Avoid common words and patterns")
        
        return suggestions
    
    @classmethod
    @guarded
    def get_stats(cls) -> Dict[str, int]:
        """Get password service statistics."""
        return cls._stats.copy()
```

### JWT Service

```python
# services/jwt_service.py
import jwt
import uuid
from datetime import datetime, timedelta
from typing import ClassVar, Optional, Dict, Any
from singleton_service import BaseService, requires, guarded
from .config import ConfigService

@requires(ConfigService)
class JWTService(BaseService):
    """JWT token generation and validation service."""
    
    _stats: ClassVar[Dict[str, int]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize JWT service."""
        cls._stats = {
            "tokens_generated": 0,
            "tokens_validated": 0,
            "tokens_expired": 0,
            "tokens_invalid": 0
        }
    
    @classmethod
    @guarded
    def generate_token(cls, user_id: int, username: str, roles: List[str] = None, custom_claims: Dict[str, Any] = None) -> str:
        """Generate a JWT token with user information."""
        config = ConfigService.get_config()
        
        now = datetime.utcnow()
        expiry = now + timedelta(hours=config.jwt_expiry_hours)
        
        # Standard claims
        payload = {
            "iss": "auth-service",  # Issuer
            "sub": str(user_id),    # Subject (user ID)
            "aud": "api",           # Audience
            "exp": expiry,          # Expiration time
            "iat": now,             # Issued at
            "nbf": now,             # Not before
            "jti": str(uuid.uuid4()), # JWT ID (unique identifier)
            
            # Custom claims
            "username": username,
            "roles": roles or [],
        }
        
        # Add any additional custom claims
        if custom_claims:
            payload.update(custom_claims)
        
        try:
            token = jwt.encode(
                payload,
                config.jwt_secret_key,
                algorithm=config.jwt_algorithm
            )
            
            cls._stats["tokens_generated"] += 1
            return token
            
        except Exception as e:
            raise RuntimeError(f"Token generation failed: {e}")
    
    @classmethod
    @guarded
    def validate_token(cls, token: str) -> Optional[Dict[str, Any]]:
        """Validate a JWT token and return payload if valid."""
        config = ConfigService.get_config()
        
        try:
            payload = jwt.decode(
                token,
                config.jwt_secret_key,
                algorithms=[config.jwt_algorithm],
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                    "verify_aud": True
                },
                audience="api"
            )
            
            cls._stats["tokens_validated"] += 1
            return payload
            
        except jwt.ExpiredSignatureError:
            cls._stats["tokens_expired"] += 1
            return None
        except jwt.InvalidTokenError:
            cls._stats["tokens_invalid"] += 1
            return None
        except Exception as e:
            cls._stats["tokens_invalid"] += 1
            raise RuntimeError(f"Token validation failed: {e}")
    
    @classmethod
    @guarded
    def decode_token_without_verification(cls, token: str) -> Optional[Dict[str, Any]]:
        """Decode token without verification (for debugging/inspection)."""
        try:
            payload = jwt.decode(
                token,
                options={"verify_signature": False}
            )
            return payload
        except Exception:
            return None
    
    @classmethod
    @guarded
    def refresh_token(cls, token: str) -> Optional[str]:
        """Refresh a token if it's valid and not expired."""
        payload = cls.validate_token(token)
        if not payload:
            return None
        
        # Generate new token with same user info but new expiry
        return cls.generate_token(
            user_id=int(payload["sub"]),
            username=payload["username"],
            roles=payload.get("roles", []),
            custom_claims={k: v for k, v in payload.items() 
                          if k not in ["exp", "iat", "nbf", "jti", "sub", "username", "roles"]}
        )
    
    @classmethod
    @guarded
    def get_token_info(cls, token: str) -> Dict[str, Any]:
        """Get detailed information about a token."""
        # Decode without verification to inspect
        payload = cls.decode_token_without_verification(token)
        if not payload:
            return {"valid": False, "error": "Invalid token format"}
        
        now = datetime.utcnow()
        
        # Check expiration
        exp_timestamp = payload.get("exp")
        if exp_timestamp:
            exp_date = datetime.fromtimestamp(exp_timestamp)
            is_expired = exp_date < now
            time_until_expiry = exp_date - now if not is_expired else None
        else:
            is_expired = False
            time_until_expiry = None
        
        # Check if token is currently valid
        is_valid = cls.validate_token(token) is not None
        
        return {
            "valid": is_valid,
            "expired": is_expired,
            "user_id": payload.get("sub"),
            "username": payload.get("username"),
            "roles": payload.get("roles", []),
            "issued_at": datetime.fromtimestamp(payload["iat"]) if payload.get("iat") else None,
            "expires_at": datetime.fromtimestamp(exp_timestamp) if exp_timestamp else None,
            "time_until_expiry": str(time_until_expiry) if time_until_expiry else None,
            "token_id": payload.get("jti"),
            "issuer": payload.get("iss"),
            "audience": payload.get("aud")
        }
    
    @classmethod
    @guarded
    def get_stats(cls) -> Dict[str, Any]:
        """Get JWT service statistics."""
        total_tokens = cls._stats["tokens_validated"] + cls._stats["tokens_expired"] + cls._stats["tokens_invalid"]
        success_rate = cls._stats["tokens_validated"] / max(total_tokens, 1) * 100
        
        return {
            **cls._stats,
            "total_validations": total_tokens,
            "success_rate_percent": round(success_rate, 2)
        }
```

### Auth Service (Main Service)

```python
# services/auth.py
import time
import uuid
from datetime import datetime, timedelta
from typing import ClassVar, Optional, Dict, Any, List
from dataclasses import dataclass
from singleton_service import BaseService, requires, guarded
from .config import ConfigService
from .session_storage import SessionStorageService
from .password import PasswordService
from .jwt_service import JWTService

@dataclass
class AuthUser:
    """Authenticated user information."""
    user_id: int
    username: str
    email: str
    roles: List[str]
    session_id: Optional[str] = None
    token: Optional[str] = None

@dataclass
class LoginAttempt:
    """Login attempt tracking."""
    username: str
    ip_address: str
    success: bool
    timestamp: datetime
    error_message: Optional[str] = None

@requires(ConfigService, SessionStorageService, PasswordService, JWTService)
class AuthService(BaseService):
    """Comprehensive authentication service."""
    
    _login_attempts: ClassVar[Dict[str, List[LoginAttempt]]] = {}
    _locked_accounts: ClassVar[Dict[str, datetime]] = {}
    _auth_stats: ClassVar[Dict[str, int]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize authentication service."""
        cls._login_attempts = {}
        cls._locked_accounts = {}
        cls._auth_stats = {
            "successful_logins": 0,
            "failed_logins": 0,
            "sessions_created": 0,
            "sessions_destroyed": 0,
            "password_changes": 0,
            "account_lockouts": 0
        }
    
    @classmethod
    @guarded
    def authenticate(cls, username: str, password: str, password_hash: str, 
                    user_data: Dict[str, Any], ip_address: str = "unknown") -> AuthUser:
        """Authenticate user with credentials."""
        
        # Check if account is locked
        if cls._is_account_locked(username):
            cls._record_login_attempt(username, ip_address, False, "Account locked")
            raise ValueError("Account is temporarily locked due to too many failed attempts")
        
        # Verify password
        if not PasswordService.verify_password(password, password_hash):
            cls._record_failed_login(username, ip_address)
            raise ValueError("Invalid username or password")
        
        # Successful authentication
        cls._clear_failed_attempts(username)
        cls._record_login_attempt(username, ip_address, True)
        cls._auth_stats["successful_logins"] += 1
        
        # Create session and token
        session_id = str(uuid.uuid4())
        token = JWTService.generate_token(
            user_id=user_data["id"],
            username=username,
            roles=user_data.get("roles", [])
        )
        
        # Store session
        session_data = {
            "user_id": user_data["id"],
            "username": username,
            "email": user_data["email"],
            "roles": user_data.get("roles", []),
            "ip_address": ip_address,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat()
        }
        
        SessionStorageService.create_session(session_id, session_data)
        cls._auth_stats["sessions_created"] += 1
        
        return AuthUser(
            user_id=user_data["id"],
            username=username,
            email=user_data["email"],
            roles=user_data.get("roles", []),
            session_id=session_id,
            token=token
        )
    
    @classmethod
    @guarded
    def validate_session(cls, session_id: str) -> Optional[AuthUser]:
        """Validate session and return user if valid."""
        session_data = SessionStorageService.get_session(session_id)
        if not session_data:
            return None
        
        # Update last activity
        session_data["last_activity"] = datetime.utcnow().isoformat()
        SessionStorageService.update_session(session_id, session_data)
        
        return AuthUser(
            user_id=session_data["user_id"],
            username=session_data["username"],
            email=session_data["email"],
            roles=session_data["roles"],
            session_id=session_id
        )
    
    @classmethod
    @guarded
    def validate_token(cls, token: str) -> Optional[AuthUser]:
        """Validate JWT token and return user if valid."""
        payload = JWTService.validate_token(token)
        if not payload:
            return None
        
        return AuthUser(
            user_id=int(payload["sub"]),
            username=payload["username"],
            email=payload.get("email", ""),
            roles=payload.get("roles", []),
            token=token
        )
    
    @classmethod
    @guarded
    def logout(cls, session_id: Optional[str] = None, token: Optional[str] = None) -> bool:
        """Logout user by destroying session and/or invalidating token."""
        success = False
        
        if session_id:
            success = SessionStorageService.delete_session(session_id)
            if success:
                cls._auth_stats["sessions_destroyed"] += 1
        
        # Note: JWT tokens can't be invalidated without a blacklist
        # In production, you might want to maintain a blacklist of invalidated tokens
        
        return success
    
    @classmethod
    @guarded
    def change_password(cls, username: str, old_password: str, new_password: str, 
                       current_password_hash: str) -> str:
        """Change user password with validation."""
        
        # Verify current password
        if not PasswordService.verify_password(old_password, current_password_hash):
            raise ValueError("Current password is incorrect")
        
        # Check new password strength
        strength_check = PasswordService.check_password_strength(new_password)
        if not strength_check["is_valid"]:
            suggestions = "; ".join(strength_check["suggestions"])
            raise ValueError(f"New password is too weak. {suggestions}")
        
        # Hash new password
        new_password_hash = PasswordService.hash_password(new_password)
        cls._auth_stats["password_changes"] += 1
        
        return new_password_hash
    
    @classmethod
    @guarded
    def check_permissions(cls, user: AuthUser, required_roles: List[str]) -> bool:
        """Check if user has required roles."""
        if not required_roles:
            return True
        
        user_roles = set(user.roles)
        required_roles_set = set(required_roles)
        
        # Check if user has any of the required roles
        return bool(user_roles.intersection(required_roles_set))
    
    @classmethod
    @guarded
    def extend_session(cls, session_id: str, hours: int = 24) -> bool:
        """Extend session expiration."""
        return SessionStorageService.extend_session(session_id, hours)
    
    @classmethod
    @guarded
    def get_active_sessions(cls, username: str) -> List[Dict[str, Any]]:
        """Get all active sessions for a user (simplified implementation)."""
        # In a real implementation, you'd query Redis by user
        # This is a simplified version
        return []
    
    @classmethod
    @guarded
    def revoke_all_sessions(cls, username: str) -> int:
        """Revoke all sessions for a user."""
        # In a real implementation, you'd find and delete all user sessions
        # This is a simplified version
        return 0
    
    @classmethod
    def _is_account_locked(cls, username: str) -> bool:
        """Check if account is currently locked."""
        if username not in cls._locked_accounts:
            return False
        
        config = ConfigService.get_config()
        lockout_end = cls._locked_accounts[username]
        lockout_duration = timedelta(minutes=config.lockout_duration_minutes)
        
        if datetime.utcnow() >= lockout_end + lockout_duration:
            # Lockout period has ended
            del cls._locked_accounts[username]
            return False
        
        return True
    
    @classmethod
    def _record_failed_login(cls, username: str, ip_address: str) -> None:
        """Record failed login attempt and check for lockout."""
        cls._record_login_attempt(username, ip_address, False, "Invalid credentials")
        
        config = ConfigService.get_config()
        
        # Get recent failed attempts
        recent_failures = cls._get_recent_failed_attempts(username, minutes=60)
        
        if len(recent_failures) >= config.max_login_attempts:
            cls._locked_accounts[username] = datetime.utcnow()
            cls._auth_stats["account_lockouts"] += 1
    
    @classmethod
    def _record_login_attempt(cls, username: str, ip_address: str, success: bool, 
                            error_message: Optional[str] = None) -> None:
        """Record login attempt."""
        if username not in cls._login_attempts:
            cls._login_attempts[username] = []
        
        attempt = LoginAttempt(
            username=username,
            ip_address=ip_address,
            success=success,
            timestamp=datetime.utcnow(),
            error_message=error_message
        )
        
        cls._login_attempts[username].append(attempt)
        
        if not success:
            cls._auth_stats["failed_logins"] += 1
        
        # Keep only last 100 attempts per user
        cls._login_attempts[username] = cls._login_attempts[username][-100:]
    
    @classmethod
    def _get_recent_failed_attempts(cls, username: str, minutes: int) -> List[LoginAttempt]:
        """Get recent failed login attempts."""
        if username not in cls._login_attempts:
            return []
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        return [
            attempt for attempt in cls._login_attempts[username]
            if not attempt.success and attempt.timestamp >= cutoff_time
        ]
    
    @classmethod
    def _clear_failed_attempts(cls, username: str) -> None:
        """Clear failed login attempts after successful login."""
        if username in cls._login_attempts:
            # Keep only successful attempts
            cls._login_attempts[username] = [
                attempt for attempt in cls._login_attempts[username]
                if attempt.success
            ]
    
    @classmethod
    @guarded
    def get_login_history(cls, username: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get login history for a user."""
        if username not in cls._login_attempts:
            return []
        
        attempts = cls._login_attempts[username][-limit:]
        
        return [
            {
                "timestamp": attempt.timestamp.isoformat(),
                "ip_address": attempt.ip_address,
                "success": attempt.success,
                "error_message": attempt.error_message
            }
            for attempt in reversed(attempts)
        ]
    
    @classmethod
    @guarded
    def get_security_stats(cls) -> Dict[str, Any]:
        """Get comprehensive security statistics."""
        config = ConfigService.get_config()
        
        # Count locked accounts
        locked_count = len([
            username for username, lockout_time in cls._locked_accounts.items()
            if datetime.utcnow() < lockout_time + timedelta(minutes=config.lockout_duration_minutes)
        ])
        
        return {
            **cls._auth_stats,
            "active_sessions": SessionStorageService.get_active_sessions_count(),
            "locked_accounts": locked_count,
            "total_users_with_attempts": len(cls._login_attempts),
            "password_stats": PasswordService.get_stats(),
            "jwt_stats": JWTService.get_stats(),
            "session_stats": SessionStorageService.get_stats()
        }
```

## 🚀 Usage Examples

### Basic Authentication

```python
# main.py
import os
from dotenv import load_dotenv
from services.auth import AuthService
from services.password import PasswordService

def main():
    load_dotenv()
    
    # Set environment variables
    os.environ["JWT_SECRET_KEY"] = "your-super-secret-jwt-key-at-least-32-chars-long"
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"
    
    try:
        # Simulate user data (normally from database)
        user_password = "SecurePass123!"
        password_hash = PasswordService.hash_password(user_password)
        
        user_data = {
            "id": 1,
            "email": "john@example.com",
            "roles": ["user", "admin"]
        }
        
        # Authenticate user
        auth_user = AuthService.authenticate(
            username="john_doe",
            password=user_password,
            password_hash=password_hash,
            user_data=user_data,
            ip_address="192.168.1.100"
        )
        
        print(f"Login successful!")
        print(f"User: {auth_user.username}")
        print(f"Roles: {auth_user.roles}")
        print(f"Session ID: {auth_user.session_id}")
        print(f"Token: {auth_user.token[:50]}...")
        
        # Validate session
        session_user = AuthService.validate_session(auth_user.session_id)
        print(f"Session valid: {session_user is not None}")
        
        # Validate token
        token_user = AuthService.validate_token(auth_user.token)
        print(f"Token valid: {token_user is not None}")
        
        # Check permissions
        has_admin = AuthService.check_permissions(auth_user, ["admin"])
        print(f"Has admin role: {has_admin}")
        
        # Get security stats
        stats = AuthService.get_security_stats()
        print(f"Security stats: {stats}")
        
        # Logout
        AuthService.logout(session_id=auth_user.session_id)
        print("Logged out successfully")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
```

### Web Framework Integration (FastAPI)

```python
# fastapi_integration.py
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from services.auth import AuthService, AuthUser

app = FastAPI(title="Auth Service API")
security = HTTPBearer()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token: str
    session_id: str
    user: dict

class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str

# Dependency to get current user from token
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> AuthUser:
    """Extract and validate user from JWT token."""
    try:
        user = AuthService.validate_token(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

# Dependency to check admin role
def require_admin_role(current_user: AuthUser = Depends(get_current_user)) -> AuthUser:
    """Require admin role for access."""
    if not AuthService.check_permissions(current_user, ["admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    return current_user

@app.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Login endpoint."""
    try:
        # In real app, get user data from database
        # This is a simplified example
        user_data = {
            "id": 1,
            "email": "john@example.com",
            "roles": ["user"]
        }
        
        # Get stored password hash (from database)
        password_hash = "$2b$12$example_hash"  # Replace with real hash
        
        auth_user = AuthService.authenticate(
            username=request.username,
            password=request.password,
            password_hash=password_hash,
            user_data=user_data
        )
        
        return LoginResponse(
            token=auth_user.token,
            session_id=auth_user.session_id,
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

@app.post("/auth/logout")
async def logout(current_user: AuthUser = Depends(get_current_user)):
    """Logout endpoint."""
    success = AuthService.logout(session_id=current_user.session_id)
    return {"message": "Logged out successfully", "success": success}

@app.get("/auth/me")
async def get_current_user_info(current_user: AuthUser = Depends(get_current_user)):
    """Get current user information."""
    return {
        "id": current_user.user_id,
        "username": current_user.username,
        "email": current_user.email,
        "roles": current_user.roles
    }

@app.post("/auth/change-password")
async def change_password(
    request: PasswordChangeRequest,
    current_user: AuthUser = Depends(get_current_user)
):
    """Change password endpoint."""
    try:
        # Get current password hash (from database)
        current_hash = "$2b$12$example_hash"  # Replace with real hash
        
        new_hash = AuthService.change_password(
            username=current_user.username,
            old_password=request.old_password,
            new_password=request.new_password,
            current_password_hash=current_hash
        )
        
        # Save new hash to database here
        
        return {"message": "Password changed successfully"}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@app.get("/auth/stats")
async def get_security_stats(admin_user: AuthUser = Depends(require_admin_role)):
    """Get security statistics (admin only)."""
    return AuthService.get_security_stats()

@app.get("/auth/login-history/{username}")
async def get_login_history(
    username: str,
    admin_user: AuthUser = Depends(require_admin_role)
):
    """Get user login history (admin only)."""
    return AuthService.get_login_history(username)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## 🧪 Testing

### Unit Tests

```python
# test_auth.py
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from services.auth import AuthService, AuthUser
from services.password import PasswordService
from services.jwt_service import JWTService

class TestAuthService:
    def setup_method(self):
        """Reset services before each test."""
        for service in [AuthService, PasswordService, JWTService]:
            service._initialized = False
    
    def test_successful_authentication(self):
        """Test successful user authentication."""
        password = "TestPass123!"
        password_hash = "$2b$12$mock_hash"
        user_data = {
            "id": 1,
            "email": "test@example.com",
            "roles": ["user"]
        }
        
        with patch.object(PasswordService, 'verify_password', return_value=True), \
             patch.object(JWTService, 'generate_token', return_value="mock_token"), \
             patch.object(AuthService, '_record_login_attempt'), \
             patch.object(AuthService, '_clear_failed_attempts'):
            
            auth_user = AuthService.authenticate(
                username="testuser",
                password=password,
                password_hash=password_hash,
                user_data=user_data
            )
            
            assert auth_user.username == "testuser"
            assert auth_user.user_id == 1
            assert auth_user.token == "mock_token"
            assert auth_user.session_id is not None
    
    def test_failed_authentication(self):
        """Test failed authentication with wrong password."""
        with patch.object(PasswordService, 'verify_password', return_value=False), \
             patch.object(AuthService, '_record_failed_login'):
            
            with pytest.raises(ValueError, match="Invalid username or password"):
                AuthService.authenticate(
                    username="testuser",
                    password="wrong_password",
                    password_hash="$2b$12$mock_hash",
                    user_data={"id": 1}
                )
    
    def test_account_lockout(self):
        """Test account lockout after failed attempts."""
        with patch.object(AuthService, '_is_account_locked', return_value=True), \
             patch.object(AuthService, '_record_login_attempt'):
            
            with pytest.raises(ValueError, match="Account is temporarily locked"):
                AuthService.authenticate(
                    username="testuser",
                    password="password",
                    password_hash="$2b$12$mock_hash",
                    user_data={"id": 1}
                )
    
    def test_password_change_success(self):
        """Test successful password change."""
        old_hash = "$2b$12$old_hash"
        new_hash = "$2b$12$new_hash"
        
        with patch.object(PasswordService, 'verify_password', return_value=True), \
             patch.object(PasswordService, 'check_password_strength', return_value={"is_valid": True}), \
             patch.object(PasswordService, 'hash_password', return_value=new_hash):
            
            result_hash = AuthService.change_password(
                username="testuser",
                old_password="old_password",
                new_password="NewPassword123!",
                current_password_hash=old_hash
            )
            
            assert result_hash == new_hash
    
    def test_permission_check(self):
        """Test role-based permission checking."""
        user = AuthUser(
            user_id=1,
            username="testuser",
            email="test@example.com",
            roles=["user", "editor"]
        )
        
        # User has required role
        assert AuthService.check_permissions(user, ["editor"])
        
        # User doesn't have required role
        assert not AuthService.check_permissions(user, ["admin"])
        
        # No roles required
        assert AuthService.check_permissions(user, [])
```

## 🎯 Key Patterns Demonstrated

### 1. Multi-layered Security
- Password hashing with bcrypt
- JWT token-based authentication
- Session management with Redis
- Account lockout protection

### 2. Role-based Access Control
- User roles and permissions
- Permission checking utilities
- Admin-only endpoints
- Flexible authorization

### 3. Security Monitoring
- Login attempt tracking
- Account lockout management
- Security statistics
- Audit logging

### 4. Token Management
- JWT generation and validation
- Token refresh functionality
- Token inspection utilities
- Proper claims handling

### 5. Session Management
- Redis-based session storage
- Session expiration and extension
- Active session tracking
- Session cleanup

### 6. Password Security
- Strong password validation
- Secure password generation
- Password strength analysis
- bcrypt hashing with salt

## 🚀 Running the Example

1. **Install dependencies**:
```bash
pip install singleton-service pyjwt cryptography bcrypt redis python-dotenv fastapi uvicorn
```

2. **Start Redis**:
```bash
redis-server
```

3. **Set environment variables**:
```bash
export JWT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export REDIS_URL="redis://localhost:6379/0"
export JWT_EXPIRY_HOURS=24
export SESSION_EXPIRY_HOURS=168
```

4. **Run the examples**:
```bash
python main.py
python fastapi_integration.py
```

5. **Test the API**:
```bash
curl -X POST "http://localhost:8000/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"username": "john_doe", "password": "SecurePass123!"}'
```

This example demonstrates a production-ready authentication system with comprehensive security features, monitoring, and testing strategies.

---

**Next Example**: Learn user management patterns → [User Service](user-service.md)