# User Service Example

This example demonstrates a comprehensive user management service using **singleton-service**. It showcases user CRUD operations, validation, business logic, and integration with authentication and database services.

## 🎯 What You'll Learn

- User data modeling and validation
- Business logic separation from data access
- Service composition and coordination
- Input validation and sanitization
- Event-driven patterns
- Comprehensive error handling

## 📋 Complete Implementation

### Dependencies

```bash
pip install singleton-service pydantic email-validator python-dotenv sqlalchemy
```

### User Models

```python
# models/user.py
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, validator, Field
from enum import Enum

class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive" 
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"
    EDITOR = "editor"

class CreateUserRequest(BaseModel):
    """Request model for creating a new user."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    roles: List[UserRole] = Field(default=[UserRole.USER])
    
    @validator('username')
    def validate_username(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, hyphens, and underscores')
        return v.lower()
    
    @validator('first_name', 'last_name')
    def validate_names(cls, v):
        if not v.replace(' ', '').replace('-', '').replace("'", '').isalpha():
            raise ValueError('Names can only contain letters, spaces, hyphens, and apostrophes')
        return v.title()

class UpdateUserRequest(BaseModel):
    """Request model for updating user information."""
    email: Optional[EmailStr] = None
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    status: Optional[UserStatus] = None
    roles: Optional[List[UserRole]] = None
    
    @validator('first_name', 'last_name')
    def validate_names(cls, v):
        if v is not None and not v.replace(' ', '').replace('-', '').replace("'", '').isalpha():
            raise ValueError('Names can only contain letters, spaces, hyphens, and apostrophes')
        return v.title() if v else v

class UserResponse(BaseModel):
    """Response model for user data."""
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    full_name: str
    status: UserStatus
    roles: List[UserRole]
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
    is_verified: bool = False
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
    
    class Config:
        from_attributes = True

class UserListResponse(BaseModel):
    """Response model for paginated user lists."""
    users: List[UserResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_prev: bool

class PasswordChangeRequest(BaseModel):
    """Request model for password changes."""
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v

class UserProfileUpdate(BaseModel):
    """Request model for user profile updates."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    bio: Optional[str] = Field(None, max_length=500)
    phone: Optional[str] = Field(None, regex=r'^\\+?[1-9]\\d{1,14}$')
    website: Optional[str] = Field(None, regex=r'^https?://.+')
```

### Validation Service

```python
# services/validation.py
import re
from typing import Dict, List, Any, Optional
from singleton_service import BaseService, guarded

class ValidationService(BaseService):
    """Input validation and sanitization service."""
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize validation patterns."""
        # Validation patterns are compiled at class level for performance
        pass
    
    @classmethod
    @guarded
    def validate_email_uniqueness(cls, email: str, exclude_user_id: Optional[int] = None) -> bool:
        """Check if email is unique across users."""
        # This would typically query the database
        # For this example, we'll simulate the check
        from .database_user_repository import DatabaseUserRepository
        
        existing_user = DatabaseUserRepository.get_user_by_email(email)
        if existing_user is None:
            return True
        
        # Email is valid if it belongs to the user being updated
        return exclude_user_id is not None and existing_user.id == exclude_user_id
    
    @classmethod
    @guarded
    def validate_username_uniqueness(cls, username: str, exclude_user_id: Optional[int] = None) -> bool:
        """Check if username is unique across users."""
        from .database_user_repository import DatabaseUserRepository
        
        existing_user = DatabaseUserRepository.get_user_by_username(username)
        if existing_user is None:
            return True
        
        return exclude_user_id is not None and existing_user.id == exclude_user_id
    
    @classmethod
    @guarded
    def sanitize_user_input(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize user input data."""
        sanitized = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                # Basic sanitization
                value = value.strip()
                
                # Remove potentially dangerous characters for names
                if key in ['first_name', 'last_name']:
                    value = re.sub(r'[<>\"\'&]', '', value)
                
                # Sanitize bio text
                elif key == 'bio':
                    value = re.sub(r'[<>]', '', value)  # Remove HTML brackets
                    value = value[:500]  # Truncate to max length
                
                # Email lowercase
                elif key == 'email':
                    value = value.lower()
                
                # Username lowercase and sanitize
                elif key == 'username':
                    value = value.lower()
                    value = re.sub(r'[^a-z0-9_-]', '', value)
            
            sanitized[key] = value
        
        return sanitized
    
    @classmethod
    @guarded
    def validate_user_roles(cls, roles: List[str], requesting_user_roles: List[str]) -> bool:
        """Validate that user can assign the specified roles."""
        from models.user import UserRole
        
        # Convert to enum values for validation
        try:
            role_enums = [UserRole(role) for role in roles]
        except ValueError:
            return False
        
        # Admin can assign any role
        if UserRole.ADMIN in requesting_user_roles:
            return True
        
        # Moderators can assign user and editor roles
        if UserRole.MODERATOR in requesting_user_roles:
            allowed_roles = {UserRole.USER, UserRole.EDITOR}
            return set(role_enums).issubset(allowed_roles)
        
        # Regular users can only assign user role
        return set(role_enums) == {UserRole.USER}
    
    @classmethod
    @guarded
    def validate_phone_number(cls, phone: str) -> bool:
        """Validate phone number format."""
        # Remove all non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        # Check international format
        pattern = r'^\+?[1-9]\d{1,14}$'
        return bool(re.match(pattern, cleaned))
    
    @classmethod
    @guarded
    def validate_website_url(cls, url: str) -> bool:
        """Validate website URL format."""
        pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(pattern, url, re.IGNORECASE))
```

### Event Service

```python
# services/events.py
import json
from datetime import datetime
from typing import Dict, Any, List, Callable, ClassVar
from dataclasses import dataclass
from singleton_service import BaseService, guarded

@dataclass
class UserEvent:
    """User domain event."""
    event_type: str
    user_id: int
    data: Dict[str, Any]
    timestamp: datetime
    event_id: str

class EventService(BaseService):
    """Simple event publishing service for user domain events."""
    
    _handlers: ClassVar[Dict[str, List[Callable]]] = {}
    _event_history: ClassVar[List[UserEvent]] = []
    _stats: ClassVar[Dict[str, int]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize event service."""
        cls._handlers = {}
        cls._event_history = []
        cls._stats = {
            "events_published": 0,
            "events_handled": 0,
            "handler_errors": 0
        }
    
    @classmethod
    @guarded
    def publish(cls, event_type: str, user_id: int, data: Dict[str, Any]) -> None:
        """Publish a user domain event."""
        import uuid
        
        event = UserEvent(
            event_type=event_type,
            user_id=user_id,
            data=data,
            timestamp=datetime.utcnow(),
            event_id=str(uuid.uuid4())
        )
        
        # Store event in history
        cls._event_history.append(event)
        cls._stats["events_published"] += 1
        
        # Keep only last 1000 events
        if len(cls._event_history) > 1000:
            cls._event_history = cls._event_history[-1000:]
        
        # Notify handlers
        cls._notify_handlers(event)
    
    @classmethod
    def _notify_handlers(cls, event: UserEvent) -> None:
        """Notify all registered handlers for the event type."""
        handlers = cls._handlers.get(event.event_type, [])
        
        for handler in handlers:
            try:
                handler(event)
                cls._stats["events_handled"] += 1
            except Exception as e:
                cls._stats["handler_errors"] += 1
                # In production, you'd want proper logging here
                print(f"Event handler error: {e}")
    
    @classmethod
    @guarded
    def subscribe(cls, event_type: str, handler: Callable[[UserEvent], None]) -> None:
        """Subscribe to user domain events."""
        if event_type not in cls._handlers:
            cls._handlers[event_type] = []
        cls._handlers[event_type].append(handler)
    
    @classmethod
    @guarded
    def get_user_events(cls, user_id: int, limit: int = 50) -> List[UserEvent]:
        """Get events for a specific user."""
        user_events = [
            event for event in cls._event_history
            if event.user_id == user_id
        ]
        return sorted(user_events, key=lambda e: e.timestamp, reverse=True)[:limit]
    
    @classmethod
    @guarded
    def get_stats(cls) -> Dict[str, Any]:
        """Get event service statistics."""
        return {
            **cls._stats,
            "total_events_stored": len(cls._event_history),
            "registered_handlers": sum(len(handlers) for handlers in cls._handlers.values()),
            "event_types": list(cls._handlers.keys())
        }
```

### User Service

```python
# services/user_service.py
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from singleton_service import BaseService, requires, guarded
from models.user import (
    CreateUserRequest, UpdateUserRequest, UserResponse, UserListResponse,
    PasswordChangeRequest, UserProfileUpdate, UserStatus, UserRole
)
from .validation import ValidationService
from .events import EventService
from .auth import AuthService
from .password import PasswordService
from .database_user_repository import DatabaseUserRepository

@requires(ValidationService, EventService, AuthService, PasswordService, DatabaseUserRepository)
class UserService(BaseService):
    """Comprehensive user management service with business logic."""
    
    _stats: ClassVar[Dict[str, int]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize user service."""
        cls._stats = {
            "users_created": 0,
            "users_updated": 0,
            "users_deleted": 0,
            "password_changes": 0,
            "profile_updates": 0,
            "email_verifications": 0
        }
        
        # Subscribe to user events for logging/analytics
        EventService.subscribe("user_created", cls._log_user_created)
        EventService.subscribe("user_updated", cls._log_user_updated)
        EventService.subscribe("user_deleted", cls._log_user_deleted)
    
    @classmethod
    @guarded
    def create_user(cls, request: CreateUserRequest, created_by_user: Optional[UserResponse] = None) -> UserResponse:
        """Create a new user with validation and business logic."""
        
        # Sanitize input
        sanitized_data = ValidationService.sanitize_user_input(request.dict())
        request = CreateUserRequest(**sanitized_data)
        
        # Validate uniqueness
        if not ValidationService.validate_username_uniqueness(request.username):
            raise ValueError(f"Username '{request.username}' is already taken")
        
        if not ValidationService.validate_email_uniqueness(request.email):
            raise ValueError(f"Email '{request.email}' is already registered")
        
        # Validate roles (if user is being created by another user)
        if created_by_user:
            if not ValidationService.validate_user_roles(
                [role.value for role in request.roles], 
                [role.value for role in created_by_user.roles]
            ):
                raise ValueError("Insufficient permissions to assign the specified roles")
        
        # Hash password
        password_hash = PasswordService.hash_password(request.password)
        
        # Determine initial status
        initial_status = UserStatus.PENDING_VERIFICATION if cls._requires_email_verification() else UserStatus.ACTIVE
        
        try:
            # Create user in database
            user = DatabaseUserRepository.create_user(
                username=request.username,
                email=request.email,
                password_hash=password_hash,
                first_name=request.first_name,
                last_name=request.last_name,
                roles=[role.value for role in request.roles],
                status=initial_status.value
            )
            
            cls._stats["users_created"] += 1
            
            # Publish domain event
            EventService.publish("user_created", user.id, {
                "username": user.username,
                "email": user.email,
                "roles": user.roles,
                "created_by": created_by_user.id if created_by_user else None
            })
            
            # Send verification email if required
            if initial_status == UserStatus.PENDING_VERIFICATION:
                cls._send_verification_email(user)
            
            return cls._to_response(user)
            
        except Exception as e:
            logging.error(f"Failed to create user {request.username}: {e}")
            raise RuntimeError(f"User creation failed: {str(e)}")
    
    @classmethod
    @guarded
    def get_user_by_id(cls, user_id: int) -> Optional[UserResponse]:
        """Get user by ID."""
        user = DatabaseUserRepository.get_user_by_id(user_id)
        return cls._to_response(user) if user else None
    
    @classmethod
    @guarded
    def get_user_by_username(cls, username: str) -> Optional[UserResponse]:
        """Get user by username."""
        user = DatabaseUserRepository.get_user_by_username(username)
        return cls._to_response(user) if user else None
    
    @classmethod
    @guarded
    def get_user_by_email(cls, email: str) -> Optional[UserResponse]:
        """Get user by email."""
        user = DatabaseUserRepository.get_user_by_email(email)
        return cls._to_response(user) if user else None
    
    @classmethod
    @guarded
    def update_user(cls, user_id: int, request: UpdateUserRequest, 
                   updated_by_user: UserResponse) -> Optional[UserResponse]:
        """Update user information with validation."""
        
        # Check if user exists
        existing_user = DatabaseUserRepository.get_user_by_id(user_id)
        if not existing_user:
            return None
        
        # Check permissions (users can update themselves, admins can update anyone)
        if updated_by_user.id != user_id and UserRole.ADMIN not in updated_by_user.roles:
            raise ValueError("Insufficient permissions to update this user")
        
        # Sanitize input
        sanitized_data = ValidationService.sanitize_user_input(
            {k: v for k, v in request.dict().items() if v is not None}
        )
        
        # Validate email uniqueness if changing email
        if 'email' in sanitized_data:
            if not ValidationService.validate_email_uniqueness(sanitized_data['email'], user_id):
                raise ValueError(f"Email '{sanitized_data['email']}' is already registered")
        
        # Validate role changes
        if 'roles' in sanitized_data:
            if not ValidationService.validate_user_roles(
                sanitized_data['roles'], 
                [role.value for role in updated_by_user.roles]
            ):
                raise ValueError("Insufficient permissions to assign the specified roles")
        
        try:
            # Update user in database
            updated_user = DatabaseUserRepository.update_user(user_id, sanitized_data)
            if not updated_user:
                return None
            
            cls._stats["users_updated"] += 1
            
            # Publish domain event
            EventService.publish("user_updated", user_id, {
                "changes": sanitized_data,
                "updated_by": updated_by_user.id
            })
            
            return cls._to_response(updated_user)
            
        except Exception as e:
            logging.error(f"Failed to update user {user_id}: {e}")
            raise RuntimeError(f"User update failed: {str(e)}")
    
    @classmethod
    @guarded
    def delete_user(cls, user_id: int, deleted_by_user: UserResponse, 
                   hard_delete: bool = False) -> bool:
        """Delete or deactivate user."""
        
        # Check if user exists
        existing_user = DatabaseUserRepository.get_user_by_id(user_id)
        if not existing_user:
            return False
        
        # Check permissions
        if deleted_by_user.id != user_id and UserRole.ADMIN not in deleted_by_user.roles:
            raise ValueError("Insufficient permissions to delete this user")
        
        # Prevent self-deletion for admins (last admin protection would be more complex)
        if (deleted_by_user.id == user_id and 
            UserRole.ADMIN in deleted_by_user.roles and 
            UserRole.ADMIN in existing_user.roles):
            raise ValueError("Administrators cannot delete their own accounts")
        
        try:
            if hard_delete:
                # Permanently delete user (be very careful with this)
                success = DatabaseUserRepository.hard_delete_user(user_id)
            else:
                # Soft delete (set status to inactive)
                updated_user = DatabaseUserRepository.update_user(
                    user_id, 
                    {"status": UserStatus.INACTIVE.value}
                )
                success = updated_user is not None
            
            if success:
                cls._stats["users_deleted"] += 1
                
                # Publish domain event
                EventService.publish("user_deleted", user_id, {
                    "username": existing_user.username,
                    "hard_delete": hard_delete,
                    "deleted_by": deleted_by_user.id
                })
                
                # Revoke all user sessions
                AuthService.revoke_all_sessions(existing_user.username)
            
            return success
            
        except Exception as e:
            logging.error(f"Failed to delete user {user_id}: {e}")
            raise RuntimeError(f"User deletion failed: {str(e)}")
    
    @classmethod
    @guarded
    def change_password(cls, user_id: int, request: PasswordChangeRequest, 
                       requesting_user: UserResponse) -> bool:
        """Change user password with validation."""
        
        # Check permissions
        if requesting_user.id != user_id and UserRole.ADMIN not in requesting_user.roles:
            raise ValueError("Insufficient permissions to change this user's password")
        
        # Get current user
        user = DatabaseUserRepository.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        # For non-admin users, verify current password
        if requesting_user.id == user_id:
            if not PasswordService.verify_password(request.current_password, user.password_hash):
                raise ValueError("Current password is incorrect")
        
        # Hash new password
        new_password_hash = PasswordService.hash_password(request.new_password)
        
        try:
            # Update password in database
            success = DatabaseUserRepository.update_password(user_id, new_password_hash)
            
            if success:
                cls._stats["password_changes"] += 1
                
                # Publish domain event
                EventService.publish("password_changed", user_id, {
                    "changed_by": requesting_user.id
                })
                
                # Revoke all sessions to force re-login
                AuthService.revoke_all_sessions(user.username)
            
            return success
            
        except Exception as e:
            logging.error(f"Failed to change password for user {user_id}: {e}")
            raise RuntimeError(f"Password change failed: {str(e)}")
    
    @classmethod
    @guarded
    def update_profile(cls, user_id: int, request: UserProfileUpdate, 
                      requesting_user: UserResponse) -> Optional[UserResponse]:
        """Update user profile information."""
        
        # Check permissions (users can only update their own profile)
        if requesting_user.id != user_id:
            raise ValueError("Users can only update their own profile")
        
        # Sanitize and validate input
        update_data = ValidationService.sanitize_user_input(
            {k: v for k, v in request.dict().items() if v is not None}
        )
        
        # Additional validation for profile fields
        if 'phone' in update_data and not ValidationService.validate_phone_number(update_data['phone']):
            raise ValueError("Invalid phone number format")
        
        if 'website' in update_data and not ValidationService.validate_website_url(update_data['website']):
            raise ValueError("Invalid website URL format")
        
        # Check email uniqueness if changing
        if 'email' in update_data:
            if not ValidationService.validate_email_uniqueness(update_data['email'], user_id):
                raise ValueError(f"Email '{update_data['email']}' is already registered")
        
        try:
            updated_user = DatabaseUserRepository.update_user(user_id, update_data)
            
            if updated_user:
                cls._stats["profile_updates"] += 1
                
                # Publish domain event
                EventService.publish("profile_updated", user_id, {
                    "changes": update_data
                })
            
            return cls._to_response(updated_user) if updated_user else None
            
        except Exception as e:
            logging.error(f"Failed to update profile for user {user_id}: {e}")
            raise RuntimeError(f"Profile update failed: {str(e)}")
    
    @classmethod
    @guarded
    def list_users(cls, page: int = 1, per_page: int = 20, 
                  status_filter: Optional[UserStatus] = None,
                  role_filter: Optional[UserRole] = None,
                  search_query: Optional[str] = None,
                  requesting_user: UserResponse) -> UserListResponse:
        """List users with pagination and filtering."""
        
        # Check permissions (only admins and moderators can list users)
        if not any(role in requesting_user.roles for role in [UserRole.ADMIN, UserRole.MODERATOR]):
            raise ValueError("Insufficient permissions to list users")
        
        # Validate pagination parameters
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:
            per_page = 20
        
        try:
            # Calculate offset
            offset = (page - 1) * per_page
            
            # Build filters
            filters = {}
            if status_filter:
                filters['status'] = status_filter.value
            if role_filter:
                filters['role'] = role_filter.value
            if search_query:
                filters['search'] = search_query.strip()
            
            # Get users and total count from repository
            users, total = DatabaseUserRepository.list_users(
                offset=offset,
                limit=per_page,
                filters=filters
            )
            
            # Calculate pagination info
            total_pages = (total + per_page - 1) // per_page
            has_next = page < total_pages
            has_prev = page > 1
            
            return UserListResponse(
                users=[cls._to_response(user) for user in users],
                total=total,
                page=page,
                per_page=per_page,
                total_pages=total_pages,
                has_next=has_next,
                has_prev=has_prev
            )
            
        except Exception as e:
            logging.error(f"Failed to list users: {e}")
            raise RuntimeError(f"User listing failed: {str(e)}")
    
    @classmethod
    @guarded
    def verify_email(cls, user_id: int, verification_token: str) -> bool:
        """Verify user email address."""
        try:
            # In a real implementation, you'd validate the token
            user = DatabaseUserRepository.get_user_by_id(user_id)
            if not user:
                return False
            
            # Update user status
            updated_user = DatabaseUserRepository.update_user(user_id, {
                "status": UserStatus.ACTIVE.value,
                "is_verified": True
            })
            
            if updated_user:
                cls._stats["email_verifications"] += 1
                
                # Publish domain event
                EventService.publish("email_verified", user_id, {
                    "email": user.email
                })
            
            return updated_user is not None
            
        except Exception as e:
            logging.error(f"Failed to verify email for user {user_id}: {e}")
            return False
    
    @classmethod
    @guarded
    def get_user_stats(cls) -> Dict[str, Any]:
        """Get user service statistics."""
        # Get repository stats
        repo_stats = DatabaseUserRepository.get_stats()
        
        # Get event stats
        event_stats = EventService.get_stats()
        
        return {
            "service_stats": cls._stats,
            "repository_stats": repo_stats,
            "event_stats": event_stats
        }
    
    @classmethod
    def _to_response(cls, user: Any) -> UserResponse:
        """Convert database user to response model."""
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            status=UserStatus(user.status),
            roles=[UserRole(role) for role in user.roles],
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login_at=user.last_login_at,
            is_verified=getattr(user, 'is_verified', False)
        )
    
    @classmethod
    def _requires_email_verification(cls) -> bool:
        """Check if email verification is required for new users."""
        # This could be configurable
        return True
    
    @classmethod
    def _send_verification_email(cls, user: Any) -> None:
        """Send email verification (placeholder)."""
        # In a real implementation, you'd send an email
        logging.info(f"Verification email sent to {user.email}")
    
    # Event handlers
    @classmethod
    def _log_user_created(cls, event) -> None:
        """Log user creation event."""
        logging.info(f"User created: {event.data['username']} (ID: {event.user_id})")
    
    @classmethod
    def _log_user_updated(cls, event) -> None:
        """Log user update event."""
        logging.info(f"User updated: ID {event.user_id}, changes: {event.data['changes']}")
    
    @classmethod
    def _log_user_deleted(cls, event) -> None:
        """Log user deletion event."""
        logging.info(f"User deleted: {event.data['username']} (ID: {event.user_id})")
```

## 🚀 Usage Examples

### Basic User Management

```python
# main.py
import os
from dotenv import load_dotenv
from services.user_service import UserService
from models.user import CreateUserRequest, UpdateUserRequest, UserRole, UserStatus

def main():
    load_dotenv()
    
    try:
        # Create admin user
        admin_request = CreateUserRequest(
            username="admin_user",
            email="admin@example.com",
            password="AdminPass123!",
            first_name="Admin",
            last_name="User",
            roles=[UserRole.ADMIN]
        )
        
        admin_user = UserService.create_user(admin_request)
        print(f"Created admin user: {admin_user.username} (ID: {admin_user.id})")
        
        # Create regular user
        user_request = CreateUserRequest(
            username="john_doe",
            email="john@example.com",
            password="UserPass123!",
            first_name="John",
            last_name="Doe"
        )
        
        regular_user = UserService.create_user(user_request, created_by_user=admin_user)
        print(f"Created regular user: {regular_user.username} (ID: {regular_user.id})")
        
        # Update user information
        update_request = UpdateUserRequest(
            first_name="Jonathan",
            status=UserStatus.ACTIVE
        )
        
        updated_user = UserService.update_user(
            regular_user.id, 
            update_request, 
            updated_by_user=admin_user
        )
        print(f"Updated user: {updated_user.first_name}")
        
        # List users
        user_list = UserService.list_users(
            page=1,
            per_page=10,
            requesting_user=admin_user
        )
        print(f"Found {user_list.total} users")
        
        # Get user statistics
        stats = UserService.get_user_stats()
        print(f"Service stats: {stats['service_stats']}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
```

### FastAPI Integration

```python
# fastapi_user_api.py
from fastapi import FastAPI, HTTPException, Depends, Query, status
from fastapi.security import HTTPBearer
from typing import Optional, List
from services.user_service import UserService
from services.auth import AuthService, AuthUser
from models.user import (
    CreateUserRequest, UpdateUserRequest, UserResponse, UserListResponse,
    PasswordChangeRequest, UserProfileUpdate, UserStatus, UserRole
)

app = FastAPI(title="User Management API")
security = HTTPBearer()

def get_current_user(credentials = Depends(security)) -> AuthUser:
    """Get current authenticated user."""
    user = AuthService.validate_token(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    return user

def get_current_user_response(current_user: AuthUser = Depends(get_current_user)) -> UserResponse:
    """Get current user as UserResponse."""
    user_response = UserService.get_user_by_id(current_user.user_id)
    if not user_response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user_response

@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: CreateUserRequest,
    current_user: UserResponse = Depends(get_current_user_response)
):
    """Create a new user."""
    try:
        return UserService.create_user(request, created_by_user=current_user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.get("/users", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: Optional[UserStatus] = None,
    role_filter: Optional[UserRole] = None,
    search: Optional[str] = None,
    current_user: UserResponse = Depends(get_current_user_response)
):
    """List users with pagination and filtering."""
    try:
        return UserService.list_users(
            page=page,
            per_page=per_page,
            status_filter=status_filter,
            role_filter=role_filter,
            search_query=search,
            requesting_user=current_user
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: UserResponse = Depends(get_current_user_response)
):
    """Get user by ID."""
    user = UserService.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Check permissions - users can view their own profile, admins can view anyone
    if current_user.id != user_id and UserRole.ADMIN not in current_user.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    return user

@app.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    request: UpdateUserRequest,
    current_user: UserResponse = Depends(get_current_user_response)
):
    """Update user information."""
    try:
        updated_user = UserService.update_user(user_id, request, updated_by_user=current_user)
        if not updated_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return updated_user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    hard_delete: bool = Query(False),
    current_user: UserResponse = Depends(get_current_user_response)
):
    """Delete or deactivate user."""
    try:
        success = UserService.delete_user(
            user_id, 
            deleted_by_user=current_user,
            hard_delete=hard_delete
        )
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.post("/users/{user_id}/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    user_id: int,
    request: PasswordChangeRequest,
    current_user: UserResponse = Depends(get_current_user_response)
):
    """Change user password."""
    try:
        success = UserService.change_password(user_id, request, requesting_user=current_user)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return {"message": "Password changed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.put("/users/{user_id}/profile", response_model=UserResponse)
async def update_profile(
    user_id: int,
    request: UserProfileUpdate,
    current_user: UserResponse = Depends(get_current_user_response)
):
    """Update user profile."""
    try:
        updated_user = UserService.update_profile(user_id, request, requesting_user=current_user)
        if not updated_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return updated_user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.get("/users/me", response_model=UserResponse)
async def get_current_user_profile(current_user: UserResponse = Depends(get_current_user_response)):
    """Get current user's profile."""
    return current_user

@app.get("/admin/users/stats")
async def get_user_stats(current_user: UserResponse = Depends(get_current_user_response)):
    """Get user management statistics (admin only)."""
    if UserRole.ADMIN not in current_user.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    
    return UserService.get_user_stats()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## 🧪 Testing

### Unit Tests

```python
# test_user_service.py
import pytest
from unittest.mock import MagicMock, patch
from services.user_service import UserService
from models.user import CreateUserRequest, UserRole, UserStatus

class TestUserService:
    def setup_method(self):
        """Reset services before each test."""
        UserService._initialized = False
    
    def test_create_user_success(self):
        """Test successful user creation."""
        request = CreateUserRequest(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
            first_name="Test",
            last_name="User"
        )
        
        # Mock dependencies
        with patch.object(UserService, '_sanitize_and_validate') as mock_validate, \
             patch.object(UserService, '_create_in_database') as mock_create:
            
            mock_validate.return_value = request
            mock_create.return_value = MagicMock(id=1, username="testuser")
            
            user = UserService.create_user(request)
            
            assert user.username == "testuser"
            assert user.id == 1
    
    def test_create_user_duplicate_username(self):
        """Test error when username already exists."""
        request = CreateUserRequest(
            username="duplicate",
            email="test@example.com",
            password="TestPass123!",
            first_name="Test",
            last_name="User"
        )
        
        with patch.object(UserService, '_check_username_uniqueness', return_value=False):
            with pytest.raises(ValueError, match="Username 'duplicate' is already taken"):
                UserService.create_user(request)
```

## 🎯 Key Patterns Demonstrated

### 1. Business Logic Separation
- Clean separation between service layer and data access
- Domain validation and business rules
- Event-driven architecture

### 2. Input Validation and Sanitization
- Pydantic models for request validation
- Custom validation service
- Data sanitization and security

### 3. Permission-based Operations
- Role-based access control
- Operation-level permission checking
- User context passing

### 4. Event-Driven Architecture
- Domain events for audit logging
- Decoupled event handling
- Event history tracking

### 5. Comprehensive Error Handling
- Detailed error messages
- Appropriate HTTP status codes
- Logging and monitoring

### 6. Service Composition
- Multiple service dependencies
- Coordinated operations
- Proper initialization order

This example demonstrates production-ready user management with comprehensive business logic, validation, security, and testing patterns.

---

**Next Example**: Learn background processing → [Background Worker](background-worker.md)