# CLI Application Example

This example demonstrates a comprehensive command-line application using **singleton-service**. It showcases CLI design patterns, configuration management, and interactive features.

## 🎯 What You'll Learn

- CLI application architecture with services
- Command organization and parsing
- Configuration management
- Interactive CLI features
- Progress tracking and logging

## 📋 Complete Implementation

### Dependencies

```bash
pip install singleton-service click rich typer python-dotenv
```

### CLI Service

```python
# services/cli_service.py
import sys
import logging
from typing import ClassVar, Dict, Any, Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.panel import Panel
from singleton_service import BaseService, requires, guarded
from .config import ConfigService

@requires(ConfigService)
class CLIService(BaseService):
    """CLI interface service with rich output formatting."""
    
    _console: ClassVar[Optional[Console]] = None
    _verbose: ClassVar[bool] = False
    _quiet: ClassVar[bool] = False
    _stats: ClassVar[Dict[str, int]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize CLI service."""
        cls._console = Console()
        cls._verbose = False
        cls._quiet = False
        cls._stats = {
            "commands_executed": 0,
            "errors_encountered": 0,
            "warnings_shown": 0
        }
    
    @classmethod
    @guarded
    def set_verbosity(cls, verbose: bool = False, quiet: bool = False) -> None:
        """Set CLI verbosity level."""
        cls._verbose = verbose
        cls._quiet = quiet
        
        # Configure logging based on verbosity
        if verbose:
            logging.basicConfig(level=logging.DEBUG)
        elif quiet:
            logging.basicConfig(level=logging.ERROR)
        else:
            logging.basicConfig(level=logging.INFO)
    
    @classmethod
    @guarded
    def print_info(cls, message: str) -> None:
        """Print info message if not quiet."""
        if not cls._quiet:
            cls._console.print(f"ℹ️  {message}", style="blue")
    
    @classmethod
    @guarded
    def print_success(cls, message: str) -> None:
        """Print success message."""
        cls._console.print(f"✅ {message}", style="green")
    
    @classmethod
    @guarded
    def print_warning(cls, message: str) -> None:
        """Print warning message."""
        cls._console.print(f"⚠️  {message}", style="yellow")
        cls._stats["warnings_shown"] += 1
    
    @classmethod
    @guarded
    def print_error(cls, message: str) -> None:
        """Print error message."""
        cls._console.print(f"❌ {message}", style="red")
        cls._stats["errors_encountered"] += 1
    
    @classmethod
    @guarded
    def print_table(cls, data: list, headers: list, title: str = None) -> None:
        """Print data in a formatted table."""
        table = Table(title=title)
        
        for header in headers:
            table.add_column(header, style="cyan")
        
        for row in data:
            table.add_row(*[str(cell) for cell in row])
        
        cls._console.print(table)
    
    @classmethod
    @guarded
    def print_panel(cls, content: str, title: str = None, style: str = "blue") -> None:
        """Print content in a styled panel."""
        panel = Panel(content, title=title, border_style=style)
        cls._console.print(panel)
    
    @classmethod
    @guarded
    def confirm(cls, message: str, default: bool = False) -> bool:
        """Ask for user confirmation."""
        default_text = "Y/n" if default else "y/N"
        response = cls._console.input(f"{message} [{default_text}]: ")
        
        if not response:
            return default
        
        return response.lower().startswith('y')
    
    @classmethod
    @guarded
    def prompt(cls, message: str, password: bool = False) -> str:
        """Prompt user for input."""
        if password:
            return cls._console.input(f"{message}: ", password=True)
        else:
            return cls._console.input(f"{message}: ")
    
    @classmethod
    @guarded
    def progress_bar(cls, description: str = "Processing..."):
        """Create a progress bar context manager."""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=cls._console
        )
    
    @classmethod
    @guarded
    def record_command(cls, command_name: str) -> None:
        """Record that a command was executed."""
        cls._stats["commands_executed"] += 1
        if cls._verbose:
            cls._console.print(f"[dim]Executing command: {command_name}[/dim]")
    
    @classmethod
    @guarded
    def get_stats(cls) -> Dict[str, int]:
        """Get CLI usage statistics."""
        return cls._stats.copy()
```

### Database CLI Commands

```python
# commands/database.py
import click
from services.cli_service import CLIService
from services.database import DatabaseService
from services.user_repository import UserRepository

@click.group()
def database():
    """Database management commands."""
    pass

@database.command()
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def status(verbose):
    """Show database status and statistics."""
    CLIService.record_command("database status")
    
    try:
        with CLIService.progress_bar("Checking database status...") as progress:
            task = progress.add_task("Connecting to database...", total=100)
            
            # Check database connection
            progress.update(task, advance=30, description="Testing connection...")
            is_healthy = DatabaseService.ping()
            
            # Get pool status
            progress.update(task, advance=30, description="Getting pool status...")
            pool_status = DatabaseService.get_pool_status()
            
            # Get user stats
            progress.update(task, advance=40, description="Getting statistics...")
            user_stats = UserRepository.get_user_stats()
            
            progress.update(task, completed=100)
        
        # Display results
        if is_healthy:
            CLIService.print_success("Database connection is healthy")
        else:
            CLIService.print_error("Database connection failed")
            return
        
        # Pool status table
        pool_data = [
            ["Pool Size", pool_status["pool_size"]],
            ["Active Connections", pool_status["active_connections"]],
            ["Available Connections", pool_status["pool_size"] - pool_status["active_connections"]],
            ["Total Connections Made", pool_status["total_connections"]]
        ]
        
        CLIService.print_table(
            pool_data, 
            ["Metric", "Value"], 
            "Database Connection Pool"
        )
        
        # User statistics
        if verbose:
            user_data = [
                ["Total Users", user_stats.get("total_users", 0)],
                ["Active Users", user_stats.get("active_users", 0)],
                ["Inactive Users", user_stats.get("inactive_users", 0)]
            ]
            
            CLIService.print_table(
                user_data,
                ["Metric", "Count"],
                "User Statistics"
            )
        
    except Exception as e:
        CLIService.print_error(f"Failed to get database status: {e}")

@database.command()
@click.option('--table', '-t', help='Specific table to analyze')
@click.option('--force', '-f', is_flag=True, help='Force vacuum without confirmation')
def vacuum(table, force):
    """Run VACUUM ANALYZE on database tables."""
    CLIService.record_command("database vacuum")
    
    if not force:
        message = f"Run VACUUM ANALYZE on {'table ' + table if table else 'entire database'}?"
        if not CLIService.confirm(message):
            CLIService.print_info("Operation cancelled")
            return
    
    try:
        with CLIService.progress_bar("Running VACUUM ANALYZE...") as progress:
            task = progress.add_task("Analyzing database...", total=100)
            
            DatabaseService.vacuum_analyze(table)
            progress.update(task, completed=100)
        
        target = f"table '{table}'" if table else "database"
        CLIService.print_success(f"VACUUM ANALYZE completed for {target}")
        
    except Exception as e:
        CLIService.print_error(f"VACUUM ANALYZE failed: {e}")

@database.command()
def migrate():
    """Run database migrations."""
    CLIService.record_command("database migrate")
    
    CLIService.print_info("Running database migrations...")
    
    try:
        # Simulate migration process
        migrations = [
            "001_create_users_table",
            "002_add_user_roles",
            "003_create_sessions_table"
        ]
        
        with CLIService.progress_bar("Applying migrations...") as progress:
            task = progress.add_task("Running migrations...", total=len(migrations))
            
            for migration in migrations:
                progress.update(task, description=f"Applying {migration}...")
                # Simulate migration work
                import time
                time.sleep(0.5)
                progress.advance(task)
        
        CLIService.print_success(f"Applied {len(migrations)} migrations successfully")
        
    except Exception as e:
        CLIService.print_error(f"Migration failed: {e}")
```

### User Management Commands

```python
# commands/users.py
import click
from services.cli_service import CLIService
from services.user_service import UserService
from models.user import CreateUserRequest, UserRole, UserStatus

@click.group()
def users():
    """User management commands."""
    pass

@users.command()
@click.option('--page', '-p', default=1, help='Page number')
@click.option('--limit', '-l', default=20, help='Users per page')
@click.option('--status', type=click.Choice(['active', 'inactive', 'suspended']))
@click.option('--role', type=click.Choice(['user', 'admin', 'moderator']))
def list(page, limit, status, role):
    """List users with filtering options."""
    CLIService.record_command("users list")
    
    try:
        # Convert filters
        status_filter = UserStatus(status) if status else None
        role_filter = UserRole(role) if role else None
        
        # Create admin user for permission check
        admin_user = UserService.get_user_by_id(1)  # Assume admin exists
        if not admin_user:
            CLIService.print_error("Admin user not found. Create an admin user first.")
            return
        
        # Get user list
        user_list = UserService.list_users(
            page=page,
            per_page=limit,
            status_filter=status_filter,
            role_filter=role_filter,
            requesting_user=admin_user
        )
        
        if not user_list.users:
            CLIService.print_info("No users found matching criteria")
            return
        
        # Prepare table data
        headers = ["ID", "Username", "Email", "Status", "Roles", "Created"]
        rows = []
        
        for user in user_list.users:
            rows.append([
                user.id,
                user.username,
                user.email,
                user.status.value,
                ", ".join([role.value for role in user.roles]),
                user.created_at.strftime("%Y-%m-%d")
            ])
        
        CLIService.print_table(rows, headers, f"Users (Page {page} of {user_list.total_pages})")
        
        # Show pagination info
        CLIService.print_info(
            f"Showing {len(user_list.users)} of {user_list.total} users"
        )
        
    except Exception as e:
        CLIService.print_error(f"Failed to list users: {e}")

@users.command()
@click.option('--username', '-u', prompt=True, help='Username')
@click.option('--email', '-e', prompt=True, help='Email address')
@click.option('--password', '-p', prompt=True, hide_input=True, help='Password')
@click.option('--first-name', prompt=True, help='First name')
@click.option('--last-name', prompt=True, help='Last name')
@click.option('--admin', is_flag=True, help='Make user an admin')
def create(username, email, password, first_name, last_name, admin):
    """Create a new user."""
    CLIService.record_command("users create")
    
    try:
        # Determine roles
        roles = [UserRole.ADMIN] if admin else [UserRole.USER]
        
        # Create user request
        request = CreateUserRequest(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            roles=roles
        )
        
        # Create user
        user = UserService.create_user(request)
        
        CLIService.print_success(f"User '{user.username}' created successfully (ID: {user.id})")
        
        # Show user details
        details = f"""
Username: {user.username}
Email: {user.email}
Name: {user.first_name} {user.last_name}
Roles: {', '.join([role.value for role in user.roles])}
Status: {user.status.value}
        """.strip()
        
        CLIService.print_panel(details, "User Created", "green")
        
    except Exception as e:
        CLIService.print_error(f"Failed to create user: {e}")

@users.command()
@click.argument('user_id', type=int)
def delete(user_id):
    """Delete a user by ID."""
    CLIService.record_command("users delete")
    
    try:
        # Get user details first
        user = UserService.get_user_by_id(user_id)
        if not user:
            CLIService.print_error(f"User with ID {user_id} not found")
            return
        
        # Confirm deletion
        if not CLIService.confirm(f"Delete user '{user.username}' (ID: {user_id})?"):
            CLIService.print_info("Deletion cancelled")
            return
        
        # Get admin user for permission check
        admin_user = UserService.get_user_by_id(1)  # Assume admin exists
        
        # Delete user
        success = UserService.delete_user(user_id, deleted_by_user=admin_user)
        
        if success:
            CLIService.print_success(f"User '{user.username}' deleted successfully")
        else:
            CLIService.print_error("Failed to delete user")
        
    except Exception as e:
        CLIService.print_error(f"Failed to delete user: {e}")
```

### Main CLI Application

```python
# cli.py
import click
import sys
import os
from dotenv import load_dotenv
from services.cli_service import CLIService
from commands.database import database
from commands.users import users

@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.option('--quiet', '-q', is_flag=True, help='Quiet mode')
@click.option('--config', '-c', help='Configuration file path')
@click.version_option(version='1.0.0')
def cli(verbose, quiet, config):
    """
    Singleton Service CLI - Database and User Management Tool
    
    This CLI provides commands for managing your application's
    database and users using the singleton-service framework.
    """
    # Load environment variables
    if config:
        load_dotenv(config)
    else:
        load_dotenv()
    
    # Set CLI verbosity
    CLIService.set_verbosity(verbose=verbose, quiet=quiet)
    
    # Check required environment variables
    required_vars = ["DATABASE_URL", "JWT_SECRET_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        CLIService.print_error(f"Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)

# Add command groups
cli.add_command(database)
cli.add_command(users)

@cli.command()
def status():
    """Show overall application status."""
    CLIService.record_command("status")
    
    CLIService.print_info("Checking application status...")
    
    try:
        # Check services
        from services.database import DatabaseService
        from services.auth import AuthService
        
        services_status = {
            "Database": "✅ Healthy" if DatabaseService.ping() else "❌ Unhealthy",
            "Authentication": "✅ Healthy" if AuthService.ping() else "❌ Unhealthy"
        }
        
        # Display status
        status_text = "\\n".join([f"{service}: {status}" for service, status in services_status.items()])
        CLIService.print_panel(status_text, "Service Status", "blue")
        
        # Show CLI stats
        cli_stats = CLIService.get_stats()
        if cli_stats["commands_executed"] > 0:
            stats_data = [
                ["Commands Executed", cli_stats["commands_executed"]],
                ["Errors Encountered", cli_stats["errors_encountered"]],
                ["Warnings Shown", cli_stats["warnings_shown"]]
            ]
            CLIService.print_table(stats_data, ["Metric", "Count"], "CLI Statistics")
        
    except Exception as e:
        CLIService.print_error(f"Failed to check status: {e}")

@cli.command()
def init():
    """Initialize the application with default data."""
    CLIService.record_command("init")
    
    CLIService.print_info("Initializing application...")
    
    if not CLIService.confirm("This will create default admin user and setup database. Continue?"):
        CLIService.print_info("Initialization cancelled")
        return
    
    try:
        with CLIService.progress_bar("Initializing...") as progress:
            # Setup database
            task = progress.add_task("Setting up database...", total=100)
            
            # Run migrations
            progress.update(task, advance=30, description="Running migrations...")
            # DatabaseService would handle migrations here
            
            # Create admin user
            progress.update(task, advance=40, description="Creating admin user...")
            from services.user_service import UserService
            from models.user import CreateUserRequest, UserRole
            
            admin_request = CreateUserRequest(
                username="admin",
                email="admin@example.com",
                password="admin123",  # Should be changed immediately
                first_name="System",
                last_name="Administrator",
                roles=[UserRole.ADMIN]
            )
            
            try:
                admin_user = UserService.create_user(admin_request)
                progress.update(task, advance=30, description="Initialization complete")
                progress.update(task, completed=100)
                
                CLIService.print_success("Application initialized successfully")
                CLIService.print_warning("Default admin password is 'admin123' - please change it immediately!")
                
            except ValueError as e:
                if "already exists" in str(e):
                    CLIService.print_info("Admin user already exists")
                    progress.update(task, completed=100)
                else:
                    raise
        
    except Exception as e:
        CLIService.print_error(f"Initialization failed: {e}")

if __name__ == '__main__':
    cli()
```

## 🚀 Usage Examples

### Running CLI Commands

```bash
# Initialize application
python cli.py init

# Check application status
python cli.py status

# Database commands
python cli.py database status
python cli.py database vacuum --table users
python cli.py database migrate

# User management
python cli.py users list --page 1 --limit 10
python cli.py users create --username john --email john@example.com
python cli.py users delete 123

# With options
python cli.py --verbose users list
python cli.py --quiet database status
```

### Configuration

```bash
# .env file
DATABASE_URL=postgresql://user:pass@localhost/myapp
JWT_SECRET_KEY=your-secret-key
REDIS_URL=redis://localhost:6379/0

# Or use custom config file
python cli.py --config production.env status
```

## 🎯 Key Patterns Demonstrated

### 1. Command Organization
- Grouped commands with Click
- Modular command structure
- Consistent option handling
- Help text and documentation

### 2. Rich User Interface
- Colored output with Rich
- Progress bars and spinners
- Tables and panels
- Interactive prompts

### 3. Service Integration
- CLI service for output management
- Service dependency injection
- Error handling and logging
- Statistics tracking

### 4. Configuration Management
- Environment variable loading
- Configuration file support
- Required variable validation
- Multiple environment support

This example demonstrates a production-ready CLI application with rich user interface, proper error handling, and service integration.

---

**Next Example**: Learn testing strategies → [Testing Services](testing-services.md)