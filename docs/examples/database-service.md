# Database Service Example

This example demonstrates a comprehensive database service implementation using **singleton-service**. It showcases connection pooling, transaction management, migrations, and various database patterns.

## 🎯 What You'll Learn

- Database connection pooling and management
- Transaction handling and rollback
- Database migrations and schema management
- Query optimization and monitoring
- Testing database services

## 📋 Complete Implementation

### Dependencies

```bash
pip install singleton-service psycopg2-binary sqlalchemy alembic python-dotenv
```

### Configuration Service

```python
# services/config.py
import os
from typing import ClassVar, Optional
from dataclasses import dataclass
from singleton_service import BaseService, guarded

@dataclass
class DatabaseConfig:
    """Type-safe database configuration."""
    url: str
    pool_size: int
    max_overflow: int
    pool_timeout: int
    pool_recycle: int
    echo_sql: bool

class ConfigService(BaseService):
    """Database configuration management."""
    
    _config: ClassVar[Optional[DatabaseConfig]] = None
    
    @classmethod
    def initialize(cls) -> None:
        """Load and validate database configuration."""
        # Required database URL
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            raise ValueError(
                "DATABASE_URL environment variable is required. "
                "Example: postgresql://user:password@localhost/dbname"
            )
        
        # Optional settings with defaults
        try:
            pool_size = int(os.getenv("DB_POOL_SIZE", "5"))
            max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "10"))
            pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))
            pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "3600"))
        except ValueError as e:
            raise ValueError(f"Invalid database configuration: {e}")
        
        # Validate ranges
        if pool_size < 1 or pool_size > 100:
            raise ValueError("DB_POOL_SIZE must be between 1 and 100")
        
        if max_overflow < 0 or max_overflow > 100:
            raise ValueError("DB_MAX_OVERFLOW must be between 0 and 100")
        
        echo_sql = os.getenv("DB_ECHO_SQL", "false").lower() == "true"
        
        cls._config = DatabaseConfig(
            url=db_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            echo_sql=echo_sql
        )
    
    @classmethod
    @guarded
    def get_config(cls) -> DatabaseConfig:
        """Get validated database configuration."""
        return cls._config
```

### Database Service

```python
# services/database.py
import time
import logging
from typing import ClassVar, Optional, Dict, List, Any, ContextManager
from contextlib import contextmanager
from sqlalchemy import create_engine, text, MetaData, Table, Column, Integer, String, DateTime, Boolean
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from singleton_service import BaseService, requires, guarded
from .config import ConfigService

@requires(ConfigService)
class DatabaseService(BaseService):
    """Database service with connection pooling and transaction management."""
    
    _engine: ClassVar[Optional[Engine]] = None
    _session_factory: ClassVar[Optional[sessionmaker]] = None
    _metadata: ClassVar[Optional[MetaData]] = None
    _connection_stats: ClassVar[Dict[str, Any]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize database engine and connection pool."""
        config = ConfigService.get_config()
        
        # Create engine with connection pooling
        cls._engine = create_engine(
            config.url,
            poolclass=QueuePool,
            pool_size=config.pool_size,
            max_overflow=config.max_overflow,
            pool_timeout=config.pool_timeout,
            pool_recycle=config.pool_recycle,
            echo=config.echo_sql,
            future=True
        )
        
        # Create session factory
        cls._session_factory = sessionmaker(
            cls._engine,
            expire_on_commit=False
        )
        
        # Initialize metadata for table management
        cls._metadata = MetaData()
        
        # Initialize connection statistics
        cls._connection_stats = {
            "total_connections": 0,
            "active_connections": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "transactions_committed": 0,
            "transactions_rolled_back": 0
        }
        
        logging.info(f"Database initialized with pool size {config.pool_size}")
    
    @classmethod
    def ping(cls) -> bool:
        """Test database connectivity."""
        try:
            with cls._get_connection() as conn:
                result = conn.execute(text("SELECT 1")).fetchone()
                return result[0] == 1
        except Exception as e:
            logging.error(f"Database ping failed: {e}")
            return False
    
    @classmethod
    @contextmanager
    def _get_connection(cls):
        """Get database connection from pool."""
        connection = None
        try:
            cls._connection_stats["total_connections"] += 1
            cls._connection_stats["active_connections"] += 1
            
            connection = cls._engine.connect()
            yield connection
            
        finally:
            if connection:
                connection.close()
                cls._connection_stats["active_connections"] -= 1
    
    @classmethod
    @contextmanager
    def get_session(cls) -> ContextManager[Session]:
        """Get database session for ORM operations."""
        session = None
        try:
            cls._connection_stats["total_connections"] += 1
            cls._connection_stats["active_connections"] += 1
            
            session = cls._session_factory()
            yield session
            
        finally:
            if session:
                session.close()
                cls._connection_stats["active_connections"] -= 1
    
    @classmethod
    @contextmanager
    def transaction(cls) -> ContextManager[Session]:
        """Get database session with automatic transaction management."""
        session = None
        try:
            cls._connection_stats["total_connections"] += 1
            cls._connection_stats["active_connections"] += 1
            
            session = cls._session_factory()
            session.begin()
            
            yield session
            
            session.commit()
            cls._connection_stats["transactions_committed"] += 1
            
        except Exception as e:
            if session:
                session.rollback()
                cls._connection_stats["transactions_rolled_back"] += 1
            logging.error(f"Transaction rolled back: {e}")
            raise
            
        finally:
            if session:
                session.close()
                cls._connection_stats["active_connections"] -= 1
    
    @classmethod
    @guarded
    def execute_query(cls, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a raw SQL query and return results."""
        try:
            with cls._get_connection() as conn:
                if params:
                    result = conn.execute(text(query), params)
                else:
                    result = conn.execute(text(query))
                
                # Convert to list of dictionaries
                rows = []
                if result.returns_rows:
                    columns = result.keys()
                    for row in result:
                        rows.append(dict(zip(columns, row)))
                
                cls._connection_stats["successful_queries"] += 1
                return rows
                
        except Exception as e:
            cls._connection_stats["failed_queries"] += 1
            logging.error(f"Query execution failed: {e}")
            raise RuntimeError(f"Database query failed: {e}")
    
    @classmethod
    @guarded
    def execute_many(cls, query: str, params_list: List[Dict[str, Any]]) -> int:
        """Execute a query multiple times with different parameters."""
        try:
            with cls._get_connection() as conn:
                with conn.begin():
                    result = conn.execute(text(query), params_list)
                    affected_rows = result.rowcount if result.rowcount else len(params_list)
                
                cls._connection_stats["successful_queries"] += 1
                cls._connection_stats["transactions_committed"] += 1
                return affected_rows
                
        except Exception as e:
            cls._connection_stats["failed_queries"] += 1
            cls._connection_stats["transactions_rolled_back"] += 1
            logging.error(f"Batch execution failed: {e}")
            raise RuntimeError(f"Batch database operation failed: {e}")
    
    @classmethod
    @guarded
    def get_table_info(cls, table_name: str) -> Dict[str, Any]:
        """Get information about a database table."""
        try:
            # Get table columns
            columns_query = \"\"\"
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = :table_name
                ORDER BY ordinal_position
            \"\"\"
            
            columns = cls.execute_query(columns_query, {"table_name": table_name})
            
            # Get row count
            count_query = f"SELECT COUNT(*) as row_count FROM {table_name}"
            count_result = cls.execute_query(count_query)
            row_count = count_result[0]["row_count"] if count_result else 0
            
            return {
                "table_name": table_name,
                "columns": columns,
                "row_count": row_count
            }
            
        except Exception as e:
            raise RuntimeError(f"Failed to get table info for {table_name}: {e}")
    
    @classmethod
    @guarded
    def get_pool_status(cls) -> Dict[str, Any]:
        """Get connection pool status information."""
        pool = cls._engine.pool
        
        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid(),
            **cls._connection_stats
        }
    
    @classmethod
    @guarded
    def vacuum_analyze(cls, table_name: Optional[str] = None) -> None:
        """Run VACUUM ANALYZE on specified table or entire database."""
        try:
            if table_name:
                query = f"VACUUM ANALYZE {table_name}"
            else:
                query = "VACUUM ANALYZE"
            
            with cls._get_connection() as conn:
                # VACUUM cannot run inside a transaction
                conn.execute(text("COMMIT"))
                conn.execute(text(query))
            
            logging.info(f"VACUUM ANALYZE completed for {table_name or 'all tables'}")
            
        except Exception as e:
            logging.error(f"VACUUM ANALYZE failed: {e}")
            raise RuntimeError(f"Database maintenance failed: {e}")
```

### User Repository (Example Domain Service)

```python
# services/user_repository.py
import hashlib
from datetime import datetime
from typing import ClassVar, Optional, List, Dict, Any
from dataclasses import dataclass
from sqlalchemy import Table, Column, Integer, String, DateTime, Boolean, text
from singleton_service import BaseService, requires, guarded
from .database import DatabaseService

@dataclass
class User:
    """User data model."""
    id: Optional[int] = None
    username: str = ""
    email: str = ""
    password_hash: str = ""
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@requires(DatabaseService)
class UserRepository(BaseService):
    """User data access layer with validation and business logic."""
    
    _users_table: ClassVar[Optional[Table]] = None
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize user repository and create table if needed."""
        # Define users table schema
        cls._users_table = Table(
            'users',
            DatabaseService._metadata,
            Column('id', Integer, primary_key=True),
            Column('username', String(50), unique=True, nullable=False),
            Column('email', String(100), unique=True, nullable=False),
            Column('password_hash', String(128), nullable=False),
            Column('is_active', Boolean, default=True),
            Column('created_at', DateTime, default=datetime.utcnow),
            Column('updated_at', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        )
        
        # Create table if it doesn't exist
        cls._create_table_if_not_exists()
    
    @classmethod
    def _create_table_if_not_exists(cls) -> None:
        """Create users table if it doesn't exist."""
        try:
            with DatabaseService._get_connection() as conn:
                # Check if table exists
                result = conn.execute(text(\"\"\"
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'users'
                    )
                \"\"\")).fetchone()
                
                if not result[0]:
                    # Create the table
                    cls._users_table.create(conn)
                    logging.info("Users table created successfully")
                
        except Exception as e:
            logging.error(f"Failed to create users table: {e}")
            raise RuntimeError(f"Database schema initialization failed: {e}")
    
    @classmethod
    @guarded
    def create_user(cls, username: str, email: str, password: str) -> User:
        """Create a new user with validation."""
        # Validate input
        if not username or len(username) < 3:
            raise ValueError("Username must be at least 3 characters")
        
        if not email or "@" not in email:
            raise ValueError("Valid email address is required")
        
        if not password or len(password) < 6:
            raise ValueError("Password must be at least 6 characters")
        
        # Hash password
        password_hash = cls._hash_password(password)
        
        try:
            with DatabaseService.transaction() as session:
                # Check for existing username
                existing_user = session.execute(text(\"\"\"
                    SELECT id FROM users WHERE username = :username
                \"\"\"), {"username": username}).fetchone()
                
                if existing_user:
                    raise ValueError(f"Username '{username}' already exists")
                
                # Check for existing email
                existing_email = session.execute(text(\"\"\"
                    SELECT id FROM users WHERE email = :email
                \"\"\"), {"email": email}).fetchone()
                
                if existing_email:
                    raise ValueError(f"Email '{email}' already registered")
                
                # Create user
                result = session.execute(text(\"\"\"
                    INSERT INTO users (username, email, password_hash, created_at, updated_at)
                    VALUES (:username, :email, :password_hash, :created_at, :updated_at)
                    RETURNING id, created_at, updated_at
                \"\"\"), {
                    "username": username,
                    "email": email,
                    "password_hash": password_hash,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }).fetchone()
                
                return User(
                    id=result.id,
                    username=username,
                    email=email,
                    password_hash=password_hash,
                    is_active=True,
                    created_at=result.created_at,
                    updated_at=result.updated_at
                )
                
        except ValueError:
            raise  # Re-raise validation errors
        except Exception as e:
            logging.error(f"Failed to create user: {e}")
            raise RuntimeError(f"User creation failed: {e}")
    
    @classmethod
    @guarded
    def get_user_by_id(cls, user_id: int) -> Optional[User]:
        """Get user by ID."""
        try:
            result = DatabaseService.execute_query(\"\"\"
                SELECT id, username, email, password_hash, is_active, created_at, updated_at
                FROM users WHERE id = :user_id
            \"\"\", {"user_id": user_id})
            
            if not result:
                return None
            
            row = result[0]
            return User(
                id=row["id"],
                username=row["username"],
                email=row["email"],
                password_hash=row["password_hash"],
                is_active=row["is_active"],
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
            
        except Exception as e:
            logging.error(f"Failed to get user {user_id}: {e}")
            raise RuntimeError(f"User retrieval failed: {e}")
    
    @classmethod
    @guarded
    def get_user_by_username(cls, username: str) -> Optional[User]:
        """Get user by username."""
        try:
            result = DatabaseService.execute_query(\"\"\"
                SELECT id, username, email, password_hash, is_active, created_at, updated_at
                FROM users WHERE username = :username
            \"\"\", {"username": username})
            
            if not result:
                return None
            
            row = result[0]
            return User(
                id=row["id"],
                username=row["username"],
                email=row["email"],
                password_hash=row["password_hash"],
                is_active=row["is_active"],
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
            
        except Exception as e:
            logging.error(f"Failed to get user by username {username}: {e}")
            raise RuntimeError(f"User retrieval failed: {e}")
    
    @classmethod
    @guarded
    def update_user(cls, user_id: int, **updates) -> Optional[User]:
        """Update user with validation."""
        if not updates:
            raise ValueError("No updates provided")
        
        # Validate allowed fields
        allowed_fields = {"username", "email", "is_active"}
        invalid_fields = set(updates.keys()) - allowed_fields
        if invalid_fields:
            raise ValueError(f"Invalid fields: {invalid_fields}")
        
        try:
            with DatabaseService.transaction() as session:
                # Build dynamic update query
                set_clauses = []
                params = {"user_id": user_id, "updated_at": datetime.utcnow()}
                
                for field, value in updates.items():
                    set_clauses.append(f"{field} = :{field}")
                    params[field] = value
                
                query = f\"\"\"
                    UPDATE users 
                    SET {", ".join(set_clauses)}, updated_at = :updated_at
                    WHERE id = :user_id
                    RETURNING id, username, email, password_hash, is_active, created_at, updated_at
                \"\"\"
                
                result = session.execute(text(query), params).fetchone()
                
                if not result:
                    return None
                
                return User(
                    id=result.id,
                    username=result.username,
                    email=result.email,
                    password_hash=result.password_hash,
                    is_active=result.is_active,
                    created_at=result.created_at,
                    updated_at=result.updated_at
                )
                
        except Exception as e:
            logging.error(f"Failed to update user {user_id}: {e}")
            raise RuntimeError(f"User update failed: {e}")
    
    @classmethod
    @guarded
    def delete_user(cls, user_id: int) -> bool:
        """Soft delete user (mark as inactive)."""
        try:
            result = DatabaseService.execute_query(\"\"\"
                UPDATE users 
                SET is_active = false, updated_at = :updated_at
                WHERE id = :user_id AND is_active = true
                RETURNING id
            \"\"\", {
                "user_id": user_id,
                "updated_at": datetime.utcnow()
            })
            
            return len(result) > 0
            
        except Exception as e:
            logging.error(f"Failed to delete user {user_id}: {e}")
            raise RuntimeError(f"User deletion failed: {e}")
    
    @classmethod
    @guarded
    def list_users(cls, offset: int = 0, limit: int = 100, active_only: bool = True) -> List[User]:
        """List users with pagination."""
        if limit > 1000:
            raise ValueError("Limit cannot exceed 1000")
        
        try:
            where_clause = "WHERE is_active = true" if active_only else ""
            
            result = DatabaseService.execute_query(f\"\"\"
                SELECT id, username, email, password_hash, is_active, created_at, updated_at
                FROM users
                {where_clause}
                ORDER BY created_at DESC
                OFFSET :offset LIMIT :limit
            \"\"\", {"offset": offset, "limit": limit})
            
            users = []
            for row in result:
                users.append(User(
                    id=row["id"],
                    username=row["username"],
                    email=row["email"],
                    password_hash=row["password_hash"],
                    is_active=row["is_active"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"]
                ))
            
            return users
            
        except Exception as e:
            logging.error(f"Failed to list users: {e}")
            raise RuntimeError(f"User listing failed: {e}")
    
    @classmethod
    @guarded
    def count_users(cls, active_only: bool = True) -> int:
        """Get total user count."""
        try:
            where_clause = "WHERE is_active = true" if active_only else ""
            
            result = DatabaseService.execute_query(f\"\"\"
                SELECT COUNT(*) as count FROM users {where_clause}
            \"\"\")
            
            return result[0]["count"] if result else 0
            
        except Exception as e:
            logging.error(f"Failed to count users: {e}")
            raise RuntimeError(f"User count failed: {e}")
    
    @classmethod
    @guarded
    def verify_password(cls, username: str, password: str) -> Optional[User]:
        """Verify user password and return user if valid."""
        user = cls.get_user_by_username(username)
        if not user or not user.is_active:
            return None
        
        password_hash = cls._hash_password(password)
        if password_hash == user.password_hash:
            return user
        
        return None
    
    @classmethod
    def _hash_password(cls, password: str) -> str:
        """Hash password using SHA-256 (use bcrypt in production)."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    @classmethod
    @guarded
    def get_user_stats(cls) -> Dict[str, Any]:
        """Get user repository statistics."""
        try:
            stats = DatabaseService.execute_query(\"\"\"
                SELECT 
                    COUNT(*) as total_users,
                    COUNT(*) FILTER (WHERE is_active = true) as active_users,
                    COUNT(*) FILTER (WHERE is_active = false) as inactive_users,
                    MIN(created_at) as first_user_created,
                    MAX(created_at) as last_user_created
                FROM users
            \"\"\")
            
            if stats:
                return dict(stats[0])
            else:
                return {
                    "total_users": 0,
                    "active_users": 0,
                    "inactive_users": 0,
                    "first_user_created": None,
                    "last_user_created": None
                }
                
        except Exception as e:
            logging.error(f"Failed to get user stats: {e}")
            raise RuntimeError(f"User statistics failed: {e}")
```

## 🚀 Usage Examples

### Basic Usage

```python
# main.py
import os
from dotenv import load_dotenv
from services.user_repository import UserRepository, User

def main():
    # Load environment variables
    load_dotenv()
    
    # Set database URL
    os.environ["DATABASE_URL"] = "postgresql://user:password@localhost/testdb"
    
    try:
        # Create a new user
        user = UserRepository.create_user(
            username="john_doe",
            email="john@example.com",
            password="secure_password123"
        )
        print(f"Created user: {user.username} (ID: {user.id})")
        
        # Get user by ID
        retrieved_user = UserRepository.get_user_by_id(user.id)
        print(f"Retrieved user: {retrieved_user.email}")
        
        # Update user
        updated_user = UserRepository.update_user(
            user.id,
            email="john.doe@example.com"
        )
        print(f"Updated email: {updated_user.email}")
        
        # Verify password
        verified_user = UserRepository.verify_password("john_doe", "secure_password123")
        if verified_user:
            print("Password verification successful")
        
        # List users
        users = UserRepository.list_users(limit=10)
        print(f"Found {len(users)} users")
        
        # Get statistics
        stats = UserRepository.get_user_stats()
        print(f"User stats: {stats}")
        
        # Get database pool status
        from services.database import DatabaseService
        pool_status = DatabaseService.get_pool_status()
        print(f"Pool status: {pool_status}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
```

### Transaction Example

```python
# transaction_example.py
from services.database import DatabaseService
from services.user_repository import UserRepository

def create_users_batch():
    """Create multiple users in a single transaction."""
    users_data = [
        ("alice", "alice@example.com", "password123"),
        ("bob", "bob@example.com", "password123"),
        ("charlie", "charlie@example.com", "password123"),
    ]
    
    try:
        with DatabaseService.transaction() as session:
            created_users = []
            
            for username, email, password in users_data:
                # This would normally be done with UserRepository.create_user,
                # but here we show raw transaction usage
                password_hash = UserRepository._hash_password(password)
                
                result = session.execute(text(\"\"\"
                    INSERT INTO users (username, email, password_hash, created_at, updated_at)
                    VALUES (:username, :email, :password_hash, :created_at, :updated_at)
                    RETURNING id
                \"\"\"), {
                    "username": username,
                    "email": email,
                    "password_hash": password_hash,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }).fetchone()
                
                created_users.append((username, result.id))
            
            print(f"Successfully created {len(created_users)} users in transaction")
            return created_users
            
    except Exception as e:
        print(f"Transaction failed, all changes rolled back: {e}")
        raise

if __name__ == "__main__":
    create_users_batch()
```

### Database Maintenance

```python
# maintenance.py
from services.database import DatabaseService

def maintenance_tasks():
    """Perform database maintenance tasks."""
    try:
        # Get table information
        table_info = DatabaseService.get_table_info("users")
        print(f"Users table has {table_info['row_count']} rows")
        print(f"Columns: {[col['column_name'] for col in table_info['columns']]}")
        
        # Run VACUUM ANALYZE
        print("Running VACUUM ANALYZE...")
        DatabaseService.vacuum_analyze("users")
        print("Database maintenance completed")
        
        # Get pool status
        pool_status = DatabaseService.get_pool_status()
        print(f"Connection pool status: {pool_status}")
        
    except Exception as e:
        print(f"Maintenance failed: {e}")

if __name__ == "__main__":
    maintenance_tasks()
```

## 🧪 Testing

### Unit Tests

```python
# test_user_repository.py
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from services.user_repository import UserRepository, User
from services.database import DatabaseService

class TestUserRepository:
    def setup_method(self):
        """Reset services before each test."""
        UserRepository._initialized = False
        DatabaseService._initialized = False
    
    def test_create_user_success(self):
        """Test successful user creation."""
        expected_user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        with patch.object(DatabaseService, 'transaction') as mock_transaction:
            mock_session = MagicMock()
            mock_transaction.return_value.__enter__.return_value = mock_session
            
            # Mock existing user checks
            mock_session.execute.side_effect = [
                MagicMock(fetchone=lambda: None),  # No existing username
                MagicMock(fetchone=lambda: None),  # No existing email
                MagicMock(fetchone=lambda: MagicMock(id=1, created_at=expected_user.created_at, updated_at=expected_user.updated_at))  # Insert result
            ]
            
            user = UserRepository.create_user("testuser", "test@example.com", "password123")
            
            assert user.username == "testuser"
            assert user.email == "test@example.com"
            assert user.id == 1
    
    def test_create_user_duplicate_username(self):
        """Test error when username already exists."""
        with patch.object(DatabaseService, 'transaction') as mock_transaction:
            mock_session = MagicMock()
            mock_transaction.return_value.__enter__.return_value = mock_session
            
            # Mock existing username
            mock_session.execute.return_value.fetchone.return_value = MagicMock(id=1)
            
            with pytest.raises(ValueError, match="Username 'testuser' already exists"):
                UserRepository.create_user("testuser", "test@example.com", "password123")
    
    def test_create_user_validation(self):
        """Test input validation."""
        with pytest.raises(ValueError, match="Username must be at least 3 characters"):
            UserRepository.create_user("ab", "test@example.com", "password123")
        
        with pytest.raises(ValueError, match="Valid email address is required"):
            UserRepository.create_user("testuser", "invalid-email", "password123")
        
        with pytest.raises(ValueError, match="Password must be at least 6 characters"):
            UserRepository.create_user("testuser", "test@example.com", "12345")
    
    def test_get_user_by_id(self):
        """Test getting user by ID."""
        mock_result = [{
            "id": 1,
            "username": "testuser",
            "email": "test@example.com", 
            "password_hash": "hashed_password",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }]
        
        with patch.object(DatabaseService, 'execute_query', return_value=mock_result):
            user = UserRepository.get_user_by_id(1)
            
            assert user is not None
            assert user.id == 1
            assert user.username == "testuser"
    
    def test_get_user_by_id_not_found(self):
        """Test getting non-existent user."""
        with patch.object(DatabaseService, 'execute_query', return_value=[]):
            user = UserRepository.get_user_by_id(999)
            assert user is None
    
    def test_password_verification(self):
        """Test password verification."""
        # Test correct password
        mock_user = User(
            id=1,
            username="testuser",
            password_hash=UserRepository._hash_password("correct_password"),
            is_active=True
        )
        
        with patch.object(UserRepository, 'get_user_by_username', return_value=mock_user):
            verified_user = UserRepository.verify_password("testuser", "correct_password")
            assert verified_user is not None
            assert verified_user.username == "testuser"
        
        # Test incorrect password
        with patch.object(UserRepository, 'get_user_by_username', return_value=mock_user):
            verified_user = UserRepository.verify_password("testuser", "wrong_password")
            assert verified_user is None
```

### Integration Tests

```python
# test_integration.py
import pytest
import os
from services.database import DatabaseService
from services.user_repository import UserRepository

@pytest.mark.integration
class TestDatabaseIntegration:
    """Integration tests requiring real database."""
    
    def setup_method(self):
        """Reset services and check database."""
        DatabaseService._initialized = False
        UserRepository._initialized = False
        
        if not os.getenv("TEST_DATABASE_URL"):
            pytest.skip("TEST_DATABASE_URL not set - skipping integration tests")
        
        # Use test database
        os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL")
    
    def test_full_user_lifecycle(self):
        """Test complete user operations with real database."""
        # Create user
        user = UserRepository.create_user(
            username="integration_test",
            email="integration@test.com",
            password="test_password123"
        )
        
        assert user.id is not None
        assert user.username == "integration_test"
        
        # Get user
        retrieved = UserRepository.get_user_by_id(user.id)
        assert retrieved.username == user.username
        assert retrieved.email == user.email
        
        # Update user
        updated = UserRepository.update_user(user.id, email="updated@test.com")
        assert updated.email == "updated@test.com"
        
        # Verify password
        verified = UserRepository.verify_password("integration_test", "test_password123")
        assert verified is not None
        
        # Delete user
        deleted = UserRepository.delete_user(user.id)
        assert deleted is True
        
        # Verify user is inactive
        inactive_user = UserRepository.get_user_by_id(user.id)
        assert inactive_user.is_active is False
    
    def test_database_performance(self):
        """Test database performance with multiple operations."""
        import time
        
        # Create multiple users
        start_time = time.time()
        user_ids = []
        
        for i in range(10):
            user = UserRepository.create_user(
                username=f"perf_test_{i}",
                email=f"perf{i}@test.com",
                password="test_password123"
            )
            user_ids.append(user.id)
        
        creation_time = time.time() - start_time
        
        # Read users
        start_time = time.time()
        for user_id in user_ids:
            UserRepository.get_user_by_id(user_id)
        
        read_time = time.time() - start_time
        
        print(f"Created 10 users in {creation_time:.3f}s")
        print(f"Read 10 users in {read_time:.3f}s")
        
        # Cleanup
        for user_id in user_ids:
            UserRepository.delete_user(user_id)
```

## 🎯 Key Patterns Demonstrated

### 1. Connection Pooling
- SQLAlchemy engine with QueuePool
- Configurable pool size and overflow
- Connection lifecycle management
- Pool status monitoring

### 2. Transaction Management
- Context manager for automatic transactions
- Rollback on exceptions
- Transaction statistics tracking
- Nested transaction support

### 3. Query Patterns
- Raw SQL with parameter binding
- ORM session management
- Batch operations with execute_many
- Query performance monitoring

### 4. Schema Management
- Table creation and metadata
- Database introspection
- Migration-ready patterns
- Schema validation

### 5. Error Handling
- Connection error recovery
- Transaction rollback
- Detailed error logging
- Graceful degradation

### 6. Testing Strategies
- Service mocking for unit tests
- Integration tests with real database
- Performance testing patterns
- Test data management

## 🚀 Running the Example

1. **Set up PostgreSQL database**:
```bash
createdb singleton_service_test
```

2. **Set environment variables**:
```bash
export DATABASE_URL="postgresql://user:password@localhost/singleton_service_test"
export DB_POOL_SIZE=5
export DB_MAX_OVERFLOW=10
```

3. **Install dependencies**:
```bash
pip install singleton-service psycopg2-binary sqlalchemy python-dotenv
```

4. **Run the example**:
```bash
python main.py
python transaction_example.py
python maintenance.py
```

5. **Run tests**:
```bash
pytest test_user_repository.py
TEST_DATABASE_URL="postgresql://user:password@localhost/test_db" pytest test_integration.py -m integration
```

This example demonstrates production-ready database patterns with proper connection management, transactions, error handling, and testing strategies.

---

**Next Example**: Learn authentication patterns → [Auth Service](auth-service.md)