# Background Worker Example

This example demonstrates a background task processing system using **singleton-service**. It showcases task queues, scheduling, resource management, and monitoring patterns.

## 🎯 What You'll Learn

- Background task queue management
- Scheduled job execution
- Worker lifecycle management
- Task monitoring and retries
- Resource pooling for workers

## 📋 Complete Implementation

### Dependencies

```bash
pip install singleton-service celery redis schedule python-dotenv
```

### Task Queue Service

```python
# services/task_queue.py
import json
import uuid
from datetime import datetime, timedelta
from typing import ClassVar, Optional, Dict, Any, List, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import redis
from singleton_service import BaseService, requires, guarded
from .config import ConfigService

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

@dataclass
class Task:
    id: str
    name: str
    payload: Dict[str, Any]
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

@requires(ConfigService)
class TaskQueueService(BaseService):
    """Redis-based task queue for background processing."""
    
    _redis: ClassVar[Optional[redis.Redis]] = None
    _task_handlers: ClassVar[Dict[str, Callable]] = {}
    _stats: ClassVar[Dict[str, int]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize task queue with Redis."""
        config = ConfigService.get_config()
        
        cls._redis = redis.from_url(
            config.redis_url,
            decode_responses=True,
            socket_connect_timeout=5
        )
        
        cls._task_handlers = {}
        cls._stats = {
            "tasks_queued": 0,
            "tasks_processed": 0,
            "tasks_failed": 0,
            "tasks_retried": 0
        }
    
    @classmethod
    def ping(cls) -> bool:
        """Test Redis connectivity."""
        try:
            cls._redis.ping()
            return True
        except Exception:
            return False
    
    @classmethod
    @guarded
    def enqueue_task(cls, name: str, payload: Dict[str, Any], 
                    delay_seconds: int = 0, max_retries: int = 3) -> str:
        """Add task to queue."""
        task = Task(
            id=str(uuid.uuid4()),
            name=name,
            payload=payload,
            status=TaskStatus.PENDING,
            created_at=datetime.utcnow(),
            max_retries=max_retries
        )
        
        # Store task data
        cls._redis.hset(f"task:{task.id}", mapping=cls._task_to_dict(task))
        
        # Add to appropriate queue
        if delay_seconds > 0:
            # Delayed task
            execute_at = datetime.utcnow() + timedelta(seconds=delay_seconds)
            cls._redis.zadd("delayed_tasks", {task.id: execute_at.timestamp()})
        else:
            # Immediate task
            cls._redis.lpush("task_queue", task.id)
        
        cls._stats["tasks_queued"] += 1
        return task.id
    
    @classmethod
    @guarded
    def get_next_task(cls, timeout: int = 10) -> Optional[Task]:
        """Get next available task from queue."""
        # Check for delayed tasks that are ready
        cls._process_delayed_tasks()
        
        # Get next task from main queue
        task_id = cls._redis.brpop("task_queue", timeout=timeout)
        if not task_id:
            return None
        
        task_id = task_id[1]  # brpop returns (key, value)
        
        # Get task data
        task_data = cls._redis.hgetall(f"task:{task_id}")
        if not task_data:
            return None
        
        task = cls._dict_to_task(task_data)
        
        # Mark as running
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        cls._redis.hset(f"task:{task.id}", mapping=cls._task_to_dict(task))
        
        return task
    
    @classmethod
    @guarded
    def complete_task(cls, task_id: str, result: Any = None) -> None:
        """Mark task as completed."""
        task_data = cls._redis.hgetall(f"task:{task_id}")
        if not task_data:
            return
        
        task = cls._dict_to_task(task_data)
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()
        
        cls._redis.hset(f"task:{task.id}", mapping=cls._task_to_dict(task))
        cls._stats["tasks_processed"] += 1
        
        # Store result if provided
        if result is not None:
            cls._redis.hset(f"task:{task_id}", "result", json.dumps(result))
    
    @classmethod
    @guarded
    def fail_task(cls, task_id: str, error_message: str, retry: bool = True) -> None:
        """Mark task as failed and optionally retry."""
        task_data = cls._redis.hgetall(f"task:{task_id}")
        if not task_data:
            return
        
        task = cls._dict_to_task(task_data)
        
        if retry and task.retry_count < task.max_retries:
            # Retry the task
            task.status = TaskStatus.RETRYING
            task.retry_count += 1
            task.error_message = error_message
            
            # Add back to queue with exponential backoff
            delay = min(60 * (2 ** task.retry_count), 3600)  # Max 1 hour
            execute_at = datetime.utcnow() + timedelta(seconds=delay)
            cls._redis.zadd("delayed_tasks", {task.id: execute_at.timestamp()})
            
            cls._stats["tasks_retried"] += 1
        else:
            # Permanently failed
            task.status = TaskStatus.FAILED
            task.error_message = error_message
            task.completed_at = datetime.utcnow()
            cls._stats["tasks_failed"] += 1
        
        cls._redis.hset(f"task:{task.id}", mapping=cls._task_to_dict(task))
    
    @classmethod
    @guarded
    def register_handler(cls, task_name: str, handler: Callable) -> None:
        """Register a task handler function."""
        cls._task_handlers[task_name] = handler
    
    @classmethod
    @guarded
    def get_task_status(cls, task_id: str) -> Optional[Task]:
        """Get task status and details."""
        task_data = cls._redis.hgetall(f"task:{task_id}")
        return cls._dict_to_task(task_data) if task_data else None
    
    @classmethod
    def _process_delayed_tasks(cls) -> None:
        """Move ready delayed tasks to main queue."""
        now = datetime.utcnow().timestamp()
        ready_tasks = cls._redis.zrangebyscore("delayed_tasks", 0, now)
        
        for task_id in ready_tasks:
            cls._redis.lpush("task_queue", task_id)
            cls._redis.zrem("delayed_tasks", task_id)
    
    @classmethod
    def _task_to_dict(cls, task: Task) -> Dict[str, str]:
        """Convert task to Redis-storable dict."""
        data = asdict(task)
        data["status"] = task.status.value
        data["created_at"] = task.created_at.isoformat()
        if task.started_at:
            data["started_at"] = task.started_at.isoformat()
        if task.completed_at:
            data["completed_at"] = task.completed_at.isoformat()
        data["payload"] = json.dumps(task.payload)
        return {k: str(v) for k, v in data.items()}
    
    @classmethod
    def _dict_to_task(cls, data: Dict[str, str]) -> Task:
        """Convert Redis dict back to Task."""
        return Task(
            id=data["id"],
            name=data["name"],
            payload=json.loads(data["payload"]),
            status=TaskStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            error_message=data.get("error_message"),
            retry_count=int(data.get("retry_count", 0)),
            max_retries=int(data.get("max_retries", 3))
        )
    
    @classmethod
    @guarded
    def get_queue_stats(cls) -> Dict[str, Any]:
        """Get queue statistics."""
        pending_count = cls._redis.llen("task_queue")
        delayed_count = cls._redis.zcard("delayed_tasks")
        
        return {
            **cls._stats,
            "pending_tasks": pending_count,
            "delayed_tasks": delayed_count
        }
```

### Worker Service

```python
# services/worker.py
import time
import threading
import signal
import logging
from typing import ClassVar, Dict, Any, Optional
from singleton_service import BaseService, requires, guarded
from .task_queue import TaskQueueService, Task, TaskStatus

@requires(TaskQueueService)
class WorkerService(BaseService):
    """Background worker that processes tasks from the queue."""
    
    _workers: ClassVar[Dict[str, threading.Thread]] = {}
    _running: ClassVar[bool] = False
    _shutdown_event: ClassVar[threading.Event] = threading.Event()
    _stats: ClassVar[Dict[str, int]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize worker service."""
        cls._workers = {}
        cls._running = False
        cls._shutdown_event = threading.Event()
        cls._stats = {
            "workers_started": 0,
            "workers_stopped": 0,
            "tasks_processed": 0,
            "tasks_failed": 0,
            "processing_errors": 0
        }
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, cls._signal_handler)
        signal.signal(signal.SIGINT, cls._signal_handler)
        
        # Register some example task handlers
        TaskQueueService.register_handler("send_email", cls._handle_send_email)
        TaskQueueService.register_handler("process_image", cls._handle_process_image)
        TaskQueueService.register_handler("generate_report", cls._handle_generate_report)
    
    @classmethod
    @guarded
    def start_workers(cls, num_workers: int = 4) -> None:
        """Start background worker threads."""
        if cls._running:
            return
        
        cls._running = True
        cls._shutdown_event.clear()
        
        for i in range(num_workers):
            worker_name = f"worker-{i+1}"
            worker_thread = threading.Thread(
                target=cls._worker_loop,
                args=(worker_name,),
                name=worker_name,
                daemon=True
            )
            worker_thread.start()
            cls._workers[worker_name] = worker_thread
            cls._stats["workers_started"] += 1
        
        logging.info(f"Started {num_workers} worker threads")
    
    @classmethod
    @guarded
    def stop_workers(cls, timeout: int = 30) -> None:
        """Stop all worker threads gracefully."""
        if not cls._running:
            return
        
        logging.info("Stopping workers...")
        cls._running = False
        cls._shutdown_event.set()
        
        # Wait for workers to finish
        for worker_name, worker_thread in cls._workers.items():
            worker_thread.join(timeout=timeout)
            if worker_thread.is_alive():
                logging.warning(f"Worker {worker_name} did not stop gracefully")
            else:
                cls._stats["workers_stopped"] += 1
        
        cls._workers.clear()
        logging.info("All workers stopped")
    
    @classmethod
    def _worker_loop(cls, worker_name: str) -> None:
        """Main worker loop that processes tasks."""
        logging.info(f"Worker {worker_name} started")
        
        while cls._running and not cls._shutdown_event.is_set():
            try:
                # Get next task from queue
                task = TaskQueueService.get_next_task(timeout=5)
                if not task:
                    continue
                
                logging.info(f"Worker {worker_name} processing task {task.id}: {task.name}")
                
                # Process the task
                success = cls._process_task(task)
                
                if success:
                    cls._stats["tasks_processed"] += 1
                else:
                    cls._stats["tasks_failed"] += 1
                
            except Exception as e:
                cls._stats["processing_errors"] += 1
                logging.error(f"Worker {worker_name} error: {e}")
        
        logging.info(f"Worker {worker_name} stopped")
    
    @classmethod
    def _process_task(cls, task: Task) -> bool:
        """Process a single task."""
        try:
            # Get task handler
            handler = TaskQueueService._task_handlers.get(task.name)
            if not handler:
                TaskQueueService.fail_task(
                    task.id, 
                    f"No handler registered for task: {task.name}",
                    retry=False
                )
                return False
            
            # Execute task handler
            result = handler(task.payload)
            
            # Mark task as completed
            TaskQueueService.complete_task(task.id, result)
            return True
            
        except Exception as e:
            error_msg = f"Task execution failed: {str(e)}"
            logging.error(f"Task {task.id} failed: {error_msg}")
            
            # Mark task as failed (will retry if retries available)
            TaskQueueService.fail_task(task.id, error_msg, retry=True)
            return False
    
    @classmethod
    def _signal_handler(cls, signum, frame):
        """Handle shutdown signals."""
        logging.info(f"Received signal {signum}, shutting down workers...")
        cls.stop_workers()
    
    # Example task handlers
    @classmethod
    def _handle_send_email(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle email sending task."""
        recipient = payload.get("recipient")
        subject = payload.get("subject")
        body = payload.get("body")
        
        # Simulate email sending
        time.sleep(2)  # Simulate network delay
        
        logging.info(f"Email sent to {recipient}: {subject}")
        
        return {
            "status": "sent",
            "recipient": recipient,
            "sent_at": time.time()
        }
    
    @classmethod
    def _handle_process_image(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle image processing task."""
        image_url = payload.get("image_url")
        operations = payload.get("operations", [])
        
        # Simulate image processing
        time.sleep(5)  # Simulate processing time
        
        logging.info(f"Processed image {image_url} with operations: {operations}")
        
        return {
            "status": "processed",
            "original_url": image_url,
            "processed_url": f"{image_url}_processed.jpg",
            "operations_applied": operations
        }
    
    @classmethod
    def _handle_generate_report(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle report generation task."""
        report_type = payload.get("type")
        date_range = payload.get("date_range")
        
        # Simulate report generation
        time.sleep(10)  # Simulate heavy computation
        
        logging.info(f"Generated {report_type} report for {date_range}")
        
        return {
            "status": "generated",
            "report_type": report_type,
            "date_range": date_range,
            "file_path": f"/reports/{report_type}_{int(time.time())}.pdf"
        }
    
    @classmethod
    @guarded
    def get_worker_stats(cls) -> Dict[str, Any]:
        """Get worker statistics."""
        active_workers = len([w for w in cls._workers.values() if w.is_alive()])
        
        return {
            **cls._stats,
            "active_workers": active_workers,
            "total_workers": len(cls._workers),
            "is_running": cls._running
        }
```

### Scheduler Service

```python
# services/scheduler.py
import schedule
import threading
import time
from datetime import datetime
from typing import ClassVar, Dict, Any, List, Callable
from singleton_service import BaseService, requires, guarded
from .task_queue import TaskQueueService

@requires(TaskQueueService)
class SchedulerService(BaseService):
    """Scheduled task service using the schedule library."""
    
    _scheduler_thread: ClassVar[Optional[threading.Thread]] = None
    _running: ClassVar[bool] = False
    _jobs: ClassVar[List[schedule.Job]] = []
    _stats: ClassVar[Dict[str, int]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize scheduler service."""
        cls._scheduler_thread = None
        cls._running = False
        cls._jobs = []
        cls._stats = {
            "jobs_scheduled": 0,
            "jobs_executed": 0,
            "scheduler_errors": 0
        }
        
        # Schedule some example jobs
        cls._schedule_default_jobs()
    
    @classmethod
    @guarded
    def start_scheduler(cls) -> None:
        """Start the scheduler in a background thread."""
        if cls._running:
            return
        
        cls._running = True
        cls._scheduler_thread = threading.Thread(
            target=cls._scheduler_loop,
            name="scheduler",
            daemon=True
        )
        cls._scheduler_thread.start()
        logging.info("Scheduler started")
    
    @classmethod
    @guarded
    def stop_scheduler(cls) -> None:
        """Stop the scheduler."""
        if not cls._running:
            return
        
        cls._running = False
        if cls._scheduler_thread:
            cls._scheduler_thread.join(timeout=10)
        
        logging.info("Scheduler stopped")
    
    @classmethod
    def _scheduler_loop(cls) -> None:
        """Main scheduler loop."""
        while cls._running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                cls._stats["scheduler_errors"] += 1
                logging.error(f"Scheduler error: {e}")
    
    @classmethod
    @guarded
    def schedule_task(cls, task_name: str, payload: Dict[str, Any], 
                     cron_expression: str) -> str:
        """Schedule a recurring task."""
        def job_func():
            task_id = TaskQueueService.enqueue_task(task_name, payload)
            cls._stats["jobs_executed"] += 1
            logging.info(f"Scheduled job executed: {task_name} -> {task_id}")
        
        # Parse cron expression (simplified)
        if cron_expression == "daily":
            job = schedule.every().day.do(job_func)
        elif cron_expression == "hourly":
            job = schedule.every().hour.do(job_func)
        elif cron_expression.startswith("every "):
            # Parse "every X minutes/hours"
            parts = cron_expression.split()
            if len(parts) >= 3:
                interval = int(parts[1])
                unit = parts[2]
                if unit.startswith("minute"):
                    job = schedule.every(interval).minutes.do(job_func)
                elif unit.startswith("hour"):
                    job = schedule.every(interval).hours.do(job_func)
                else:
                    raise ValueError(f"Unsupported time unit: {unit}")
            else:
                raise ValueError(f"Invalid cron expression: {cron_expression}")
        else:
            raise ValueError(f"Unsupported cron expression: {cron_expression}")
        
        cls._jobs.append(job)
        cls._stats["jobs_scheduled"] += 1
        
        return f"job_{len(cls._jobs)}"
    
    @classmethod
    def _schedule_default_jobs(cls) -> None:
        """Schedule default maintenance jobs."""
        # Cleanup old completed tasks daily
        def cleanup_tasks():
            # This would clean up old task records
            logging.info("Cleaning up old completed tasks")
        
        # Health check every 5 minutes
        def health_check():
            TaskQueueService.enqueue_task("health_check", {
                "timestamp": datetime.utcnow().isoformat()
            })
        
        schedule.every().day.at("02:00").do(cleanup_tasks)
        schedule.every(5).minutes.do(health_check)
    
    @classmethod
    @guarded
    def get_scheduled_jobs(cls) -> List[Dict[str, Any]]:
        """Get list of scheduled jobs."""
        jobs_info = []
        for i, job in enumerate(schedule.jobs):
            jobs_info.append({
                "id": f"job_{i+1}",
                "next_run": job.next_run.isoformat() if job.next_run else None,
                "interval": str(job.interval),
                "unit": job.unit,
                "last_run": job.last_run.isoformat() if job.last_run else None
            })
        return jobs_info
    
    @classmethod
    @guarded
    def get_scheduler_stats(cls) -> Dict[str, Any]:
        """Get scheduler statistics."""
        return {
            **cls._stats,
            "is_running": cls._running,
            "total_jobs": len(cls._jobs),
            "pending_jobs": len([j for j in schedule.jobs if j.should_run])
        }
```

## 🚀 Usage Examples

### Basic Usage

```python
# main.py
import time
from services.task_queue import TaskQueueService
from services.worker import WorkerService
from services.scheduler import SchedulerService

def main():
    try:
        # Start workers
        WorkerService.start_workers(num_workers=2)
        
        # Start scheduler
        SchedulerService.start_scheduler()
        
        # Enqueue some tasks
        email_task = TaskQueueService.enqueue_task("send_email", {
            "recipient": "user@example.com",
            "subject": "Welcome!",
            "body": "Welcome to our service!"
        })
        
        image_task = TaskQueueService.enqueue_task("process_image", {
            "image_url": "https://example.com/image.jpg",
            "operations": ["resize", "compress"]
        })
        
        # Schedule a recurring task
        SchedulerService.schedule_task("generate_report", {
            "type": "daily_summary",
            "date_range": "today"
        }, "daily")
        
        print(f"Enqueued tasks: {email_task}, {image_task}")
        
        # Monitor for a while
        for i in range(30):
            time.sleep(1)
            
            # Check queue stats
            queue_stats = TaskQueueService.get_queue_stats()
            worker_stats = WorkerService.get_worker_stats()
            
            print(f"Queue: {queue_stats['pending_tasks']} pending, "
                  f"Workers: {worker_stats['active_workers']} active")
        
        # Graceful shutdown
        WorkerService.stop_workers()
        SchedulerService.stop_scheduler()
        
    except KeyboardInterrupt:
        print("Shutting down...")
        WorkerService.stop_workers()
        SchedulerService.stop_scheduler()

if __name__ == "__main__":
    main()
```

### FastAPI Integration

```python
# fastapi_worker_api.py
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional
from services.task_queue import TaskQueueService
from services.worker import WorkerService

app = FastAPI(title="Background Worker API")

class TaskRequest(BaseModel):
    name: str
    payload: Dict[str, Any]
    delay_seconds: int = 0
    max_retries: int = 3

@app.on_event("startup")
async def startup_event():
    """Start workers when API starts."""
    WorkerService.start_workers(num_workers=4)

@app.on_event("shutdown") 
async def shutdown_event():
    """Stop workers when API shuts down."""
    WorkerService.stop_workers()

@app.post("/tasks")
async def enqueue_task(request: TaskRequest):
    """Enqueue a new background task."""
    try:
        task_id = TaskQueueService.enqueue_task(
            name=request.name,
            payload=request.payload,
            delay_seconds=request.delay_seconds,
            max_retries=request.max_retries
        )
        return {"task_id": task_id, "status": "queued"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get task status and details."""
    task = TaskQueueService.get_task_status(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {
        "id": task.id,
        "name": task.name,
        "status": task.status.value,
        "created_at": task.created_at.isoformat(),
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "error_message": task.error_message,
        "retry_count": task.retry_count
    }

@app.get("/stats")
async def get_stats():
    """Get comprehensive system statistics."""
    return {
        "queue": TaskQueueService.get_queue_stats(),
        "workers": WorkerService.get_worker_stats(),
        "scheduler": SchedulerService.get_scheduler_stats()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## 🎯 Key Patterns Demonstrated

### 1. Task Queue Management
- Redis-based distributed queue
- Task serialization and persistence
- Delayed task execution
- Retry logic with exponential backoff

### 2. Worker Lifecycle
- Multi-threaded worker pool
- Graceful shutdown handling
- Signal handling for clean termination
- Worker health monitoring

### 3. Scheduled Jobs
- Cron-like scheduling
- Recurring task management
- Job registration and monitoring
- Default maintenance jobs

### 4. Error Handling
- Comprehensive retry strategies
- Error logging and tracking
- Graceful failure handling
- Dead letter queue patterns

### 5. Monitoring and Stats
- Real-time queue statistics
- Worker performance metrics
- Task execution tracking
- System health monitoring

This example demonstrates production-ready background processing with proper error handling, monitoring, and resource management.

---

**Next Example**: Learn web integration → [Web Server](web-server.md)