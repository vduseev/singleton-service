# Service Composition Example

This example demonstrates advanced service composition patterns using **singleton-service**. It showcases complex service relationships, orchestration patterns, and architectural best practices.

## 🎯 What You'll Learn

- Complex service dependency graphs
- Service orchestration patterns
- Event-driven architecture
- Command and Query Responsibility Segregation (CQRS)
- Domain-driven design with services
- Advanced error handling and resilience

## 📋 Complete Implementation

### Domain Services Architecture

```python
# services/order_domain.py
from typing import ClassVar, Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from singleton_service import BaseService, requires, guarded

class OrderStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped" 
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

@dataclass
class OrderItem:
    product_id: int
    quantity: int
    unit_price: float
    
@dataclass
class Order:
    id: Optional[int]
    user_id: int
    items: List[OrderItem]
    status: OrderStatus
    total_amount: float
    created_at: datetime
    updated_at: datetime

# Core domain services
@requires()
class ProductCatalogService(BaseService):
    """Product catalog and inventory management."""
    
    _products: ClassVar[Dict[int, Dict[str, Any]]] = {}
    _inventory: ClassVar[Dict[int, int]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        cls._products = {
            1: {"name": "Laptop", "price": 999.99, "category": "electronics"},
            2: {"name": "Book", "price": 29.99, "category": "books"},
            3: {"name": "Headphones", "price": 199.99, "category": "electronics"}
        }
        cls._inventory = {1: 50, 2: 100, 3: 25}
    
    @classmethod
    @guarded
    def get_product(cls, product_id: int) -> Optional[Dict[str, Any]]:
        return cls._products.get(product_id)
    
    @classmethod
    @guarded
    def check_availability(cls, product_id: int, quantity: int) -> bool:
        available = cls._inventory.get(product_id, 0)
        return available >= quantity
    
    @classmethod
    @guarded
    def reserve_inventory(cls, product_id: int, quantity: int) -> bool:
        if cls.check_availability(product_id, quantity):
            cls._inventory[product_id] -= quantity
            return True
        return False
    
    @classmethod
    @guarded
    def release_inventory(cls, product_id: int, quantity: int) -> None:
        cls._inventory[product_id] = cls._inventory.get(product_id, 0) + quantity

@requires()
class PaymentService(BaseService):
    """Payment processing service."""
    
    _transactions: ClassVar[Dict[str, Dict[str, Any]]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        cls._transactions = {}
    
    @classmethod
    @guarded
    def process_payment(cls, order_id: int, amount: float, payment_method: str) -> Dict[str, Any]:
        transaction_id = f"txn_{order_id}_{int(datetime.utcnow().timestamp())}"
        
        # Simulate payment processing
        import random
        success = random.random() > 0.1  # 90% success rate
        
        transaction = {
            "id": transaction_id,
            "order_id": order_id,
            "amount": amount,
            "payment_method": payment_method,
            "status": "completed" if success else "failed",
            "timestamp": datetime.utcnow()
        }
        
        cls._transactions[transaction_id] = transaction
        return transaction

@requires()
class NotificationService(BaseService):
    """Notification and messaging service."""
    
    _notifications: ClassVar[List[Dict[str, Any]]] = []
    
    @classmethod
    def initialize(cls) -> None:
        cls._notifications = []
    
    @classmethod
    @guarded
    def send_order_confirmation(cls, order: Order, user_email: str) -> None:
        notification = {
            "type": "order_confirmation",
            "order_id": order.id,
            "user_email": user_email,
            "message": f"Order #{order.id} confirmed. Total: ${order.total_amount:.2f}",
            "sent_at": datetime.utcnow()
        }
        cls._notifications.append(notification)
    
    @classmethod
    @guarded
    def send_shipping_notification(cls, order: Order, tracking_number: str) -> None:
        notification = {
            "type": "shipping_notification",
            "order_id": order.id,
            "tracking_number": tracking_number,
            "message": f"Order #{order.id} has shipped. Tracking: {tracking_number}",
            "sent_at": datetime.utcnow()
        }
        cls._notifications.append(notification)

@requires()
class AuditService(BaseService):
    """Audit logging and compliance service."""
    
    _audit_log: ClassVar[List[Dict[str, Any]]] = []
    
    @classmethod
    def initialize(cls) -> None:
        cls._audit_log = []
    
    @classmethod
    @guarded
    def log_event(cls, event_type: str, entity_id: int, details: Dict[str, Any], user_id: Optional[int] = None) -> None:
        audit_entry = {
            "event_type": event_type,
            "entity_id": entity_id,
            "entity_type": "order",
            "user_id": user_id,
            "details": details,
            "timestamp": datetime.utcnow()
        }
        cls._audit_log.append(audit_entry)
    
    @classmethod
    @guarded
    def get_audit_trail(cls, entity_id: int) -> List[Dict[str, Any]]:
        return [entry for entry in cls._audit_log if entry["entity_id"] == entity_id]
```

### Orchestration Services

```python
# services/order_orchestrator.py
@requires(ProductCatalogService, PaymentService, NotificationService, AuditService)
class OrderOrchestrationService(BaseService):
    """Orchestrates complex order workflows across multiple services."""
    
    _orders: ClassVar[Dict[int, Order]] = {}
    _order_counter: ClassVar[int] = 0
    
    @classmethod
    def initialize(cls) -> None:
        cls._orders = {}
        cls._order_counter = 0
    
    @classmethod
    @guarded
    def create_order(cls, user_id: int, items: List[Dict[str, Any]], user_email: str) -> Order:
        """Create order with full workflow orchestration."""
        cls._order_counter += 1
        order_id = cls._order_counter
        
        try:
            # Step 1: Validate and reserve inventory
            order_items = []
            total_amount = 0.0
            
            for item_data in items:
                product_id = item_data["product_id"]
                quantity = item_data["quantity"]
                
                # Get product details
                product = ProductCatalogService.get_product(product_id)
                if not product:
                    raise ValueError(f"Product {product_id} not found")
                
                # Check availability
                if not ProductCatalogService.check_availability(product_id, quantity):
                    raise ValueError(f"Insufficient inventory for product {product_id}")
                
                # Reserve inventory
                if not ProductCatalogService.reserve_inventory(product_id, quantity):
                    raise ValueError(f"Failed to reserve inventory for product {product_id}")
                
                # Create order item
                order_item = OrderItem(
                    product_id=product_id,
                    quantity=quantity,
                    unit_price=product["price"]
                )
                order_items.append(order_item)
                total_amount += product["price"] * quantity
            
            # Step 2: Create order
            order = Order(
                id=order_id,
                user_id=user_id,
                items=order_items,
                status=OrderStatus.PENDING,
                total_amount=total_amount,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            cls._orders[order_id] = order
            
            # Step 3: Audit order creation
            AuditService.log_event(
                "order_created",
                order_id,
                {
                    "user_id": user_id,
                    "total_amount": total_amount,
                    "item_count": len(order_items)
                },
                user_id
            )
            
            return order
            
        except Exception as e:
            # Rollback inventory reservations on failure
            for item_data in items:
                product_id = item_data["product_id"]
                quantity = item_data["quantity"]
                ProductCatalogService.release_inventory(product_id, quantity)
            
            AuditService.log_event(
                "order_creation_failed",
                order_id,
                {"error": str(e), "user_id": user_id},
                user_id
            )
            
            raise RuntimeError(f"Order creation failed: {e}")
    
    @classmethod
    @guarded
    def confirm_order(cls, order_id: int, payment_method: str) -> Order:
        """Confirm order with payment processing."""
        order = cls._orders.get(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        if order.status != OrderStatus.PENDING:
            raise ValueError(f"Order {order_id} cannot be confirmed in status {order.status}")
        
        try:
            # Step 1: Process payment
            payment_result = PaymentService.process_payment(
                order_id, 
                order.total_amount, 
                payment_method
            )
            
            if payment_result["status"] != "completed":
                raise ValueError("Payment processing failed")
            
            # Step 2: Update order status
            order.status = OrderStatus.CONFIRMED
            order.updated_at = datetime.utcnow()
            
            # Step 3: Send confirmation notification
            # Note: In real app, get user email from user service
            NotificationService.send_order_confirmation(order, "user@example.com")
            
            # Step 4: Audit confirmation
            AuditService.log_event(
                "order_confirmed",
                order_id,
                {
                    "payment_transaction": payment_result["id"],
                    "payment_method": payment_method,
                    "amount": order.total_amount
                },
                order.user_id
            )
            
            return order
            
        except Exception as e:
            # Release inventory on confirmation failure
            for item in order.items:
                ProductCatalogService.release_inventory(item.product_id, item.quantity)
            
            # Cancel order
            order.status = OrderStatus.CANCELLED
            order.updated_at = datetime.utcnow()
            
            AuditService.log_event(
                "order_confirmation_failed",
                order_id,
                {"error": str(e)},
                order.user_id
            )
            
            raise RuntimeError(f"Order confirmation failed: {e}")
    
    @classmethod
    @guarded
    def ship_order(cls, order_id: int, tracking_number: str) -> Order:
        """Ship confirmed order."""
        order = cls._orders.get(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        if order.status != OrderStatus.CONFIRMED:
            raise ValueError(f"Order {order_id} cannot be shipped in status {order.status}")
        
        # Update order status
        order.status = OrderStatus.SHIPPED
        order.updated_at = datetime.utcnow()
        
        # Send shipping notification
        NotificationService.send_shipping_notification(order, tracking_number)
        
        # Audit shipping
        AuditService.log_event(
            "order_shipped",
            order_id,
            {"tracking_number": tracking_number},
            order.user_id
        )
        
        return order
    
    @classmethod
    @guarded
    def cancel_order(cls, order_id: int, reason: str) -> Order:
        """Cancel order and handle cleanup."""
        order = cls._orders.get(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        if order.status in [OrderStatus.SHIPPED, OrderStatus.DELIVERED]:
            raise ValueError(f"Order {order_id} cannot be cancelled in status {order.status}")
        
        # Release inventory
        for item in order.items:
            ProductCatalogService.release_inventory(item.product_id, item.quantity)
        
        # Update order status
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.utcnow()
        
        # Audit cancellation
        AuditService.log_event(
            "order_cancelled",
            order_id,
            {"reason": reason},
            order.user_id
        )
        
        return order
    
    @classmethod
    @guarded
    def get_order(cls, order_id: int) -> Optional[Order]:
        """Get order by ID."""
        return cls._orders.get(order_id)
    
    @classmethod
    @guarded
    def get_user_orders(cls, user_id: int) -> List[Order]:
        """Get all orders for a user."""
        return [order for order in cls._orders.values() if order.user_id == user_id]
```

### CQRS Pattern Implementation

```python
# services/order_queries.py
@requires(OrderOrchestrationService, AuditService, ProductCatalogService)
class OrderQueryService(BaseService):
    """Query service for read-optimized order operations (CQRS pattern)."""
    
    _order_summaries: ClassVar[Dict[int, Dict[str, Any]]] = {}
    _user_order_index: ClassVar[Dict[int, List[int]]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        cls._order_summaries = {}
        cls._user_order_index = {}
    
    @classmethod
    @guarded
    def get_order_summary(cls, order_id: int) -> Optional[Dict[str, Any]]:
        """Get optimized order summary for display."""
        if order_id not in cls._order_summaries:
            cls._build_order_summary(order_id)
        
        return cls._order_summaries.get(order_id)
    
    @classmethod
    @guarded
    def get_user_order_history(cls, user_id: int, include_cancelled: bool = False) -> List[Dict[str, Any]]:
        """Get user order history with enriched data."""
        user_orders = OrderOrchestrationService.get_user_orders(user_id)
        
        summaries = []
        for order in user_orders:
            if not include_cancelled and order.status == OrderStatus.CANCELLED:
                continue
                
            summary = cls.get_order_summary(order.id)
            if summary:
                summaries.append(summary)
        
        return sorted(summaries, key=lambda x: x["created_at"], reverse=True)
    
    @classmethod
    @guarded
    def get_order_analytics(cls, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get order analytics and metrics."""
        all_orders = []
        
        if user_id:
            all_orders = OrderOrchestrationService.get_user_orders(user_id)
        else:
            all_orders = list(OrderOrchestrationService._orders.values())
        
        analytics = {
            "total_orders": len(all_orders),
            "total_revenue": sum(order.total_amount for order in all_orders),
            "status_breakdown": {},
            "average_order_value": 0,
            "top_products": {}
        }
        
        # Status breakdown
        for status in OrderStatus:
            count = len([o for o in all_orders if o.status == status])
            analytics["status_breakdown"][status.value] = count
        
        # Average order value
        if all_orders:
            analytics["average_order_value"] = analytics["total_revenue"] / len(all_orders)
        
        # Top products
        product_sales = {}
        for order in all_orders:
            for item in order.items:
                product_sales[item.product_id] = product_sales.get(item.product_id, 0) + item.quantity
        
        # Get product names and create top products list
        top_products = []
        for product_id, quantity in sorted(product_sales.items(), key=lambda x: x[1], reverse=True)[:5]:
            product = ProductCatalogService.get_product(product_id)
            if product:
                top_products.append({
                    "product_id": product_id,
                    "name": product["name"],
                    "quantity_sold": quantity
                })
        
        analytics["top_products"] = top_products
        
        return analytics
    
    @classmethod
    def _build_order_summary(cls, order_id: int) -> None:
        """Build enriched order summary."""
        order = OrderOrchestrationService.get_order(order_id)
        if not order:
            return
        
        # Enrich with product details
        enriched_items = []
        for item in order.items:
            product = ProductCatalogService.get_product(item.product_id)
            enriched_item = {
                "product_id": item.product_id,
                "product_name": product["name"] if product else "Unknown",
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "total_price": item.unit_price * item.quantity
            }
            enriched_items.append(enriched_item)
        
        # Get audit trail
        audit_trail = AuditService.get_audit_trail(order_id)
        
        summary = {
            "id": order.id,
            "user_id": order.user_id,
            "status": order.status.value,
            "total_amount": order.total_amount,
            "items": enriched_items,
            "item_count": len(order.items),
            "created_at": order.created_at,
            "updated_at": order.updated_at,
            "audit_events": len(audit_trail),
            "last_activity": max(event["timestamp"] for event in audit_trail) if audit_trail else order.created_at
        }
        
        cls._order_summaries[order_id] = summary
```

### Saga Pattern for Complex Workflows

```python
# services/order_saga.py
from typing import ClassVar, Dict, Any, List, Callable, Optional
from dataclasses import dataclass
from enum import Enum

class SagaStepStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATED = "compensated"

@dataclass
class SagaStep:
    name: str
    action: Callable
    compensation: Callable
    status: SagaStepStatus = SagaStepStatus.PENDING
    result: Any = None
    error: Optional[str] = None

@requires(OrderOrchestrationService, ProductCatalogService, PaymentService, NotificationService)
class OrderSagaService(BaseService):
    """Saga pattern implementation for complex order workflows."""
    
    _active_sagas: ClassVar[Dict[str, List[SagaStep]]] = {}
    
    @classmethod
    def initialize(cls) -> None:
        cls._active_sagas = {}
    
    @classmethod
    @guarded
    def execute_order_creation_saga(cls, saga_id: str, user_id: int, items: List[Dict[str, Any]], payment_method: str) -> Dict[str, Any]:
        """Execute order creation as a saga with compensation."""
        
        # Define saga steps
        steps = [
            SagaStep(
                name="validate_inventory",
                action=lambda: cls._validate_and_reserve_inventory(items),
                compensation=lambda result: cls._release_inventory(result)
            ),
            SagaStep(
                name="create_order",
                action=lambda: cls._create_order_record(user_id, items),
                compensation=lambda result: cls._delete_order_record(result)
            ),
            SagaStep(
                name="process_payment",
                action=lambda: cls._process_payment_step(saga_id, payment_method),
                compensation=lambda result: cls._refund_payment(result)
            ),
            SagaStep(
                name="send_confirmation",
                action=lambda: cls._send_confirmation_step(saga_id),
                compensation=lambda result: cls._send_cancellation_notification(saga_id)
            )
        ]
        
        cls._active_sagas[saga_id] = steps
        
        try:
            # Execute saga steps
            for i, step in enumerate(steps):
                try:
                    step.result = step.action()
                    step.status = SagaStepStatus.COMPLETED
                except Exception as e:
                    step.status = SagaStepStatus.FAILED
                    step.error = str(e)
                    
                    # Compensate completed steps in reverse order
                    for j in range(i - 1, -1, -1):
                        completed_step = steps[j]
                        try:
                            completed_step.compensation(completed_step.result)
                            completed_step.status = SagaStepStatus.COMPENSATED
                        except Exception as comp_error:
                            # Log compensation failure
                            print(f"Compensation failed for step {completed_step.name}: {comp_error}")
                    
                    raise RuntimeError(f"Saga failed at step {step.name}: {e}")
            
            # Saga completed successfully
            return {
                "saga_id": saga_id,
                "status": "completed",
                "order_id": steps[1].result,  # Order ID from create_order step
                "payment_transaction": steps[2].result
            }
            
        finally:
            # Clean up saga
            if saga_id in cls._active_sagas:
                del cls._active_sagas[saga_id]
    
    @classmethod
    def _validate_and_reserve_inventory(cls, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and reserve inventory for all items."""
        reserved_items = []
        
        try:
            for item in items:
                product_id = item["product_id"]
                quantity = item["quantity"]
                
                if not ProductCatalogService.check_availability(product_id, quantity):
                    raise ValueError(f"Insufficient inventory for product {product_id}")
                
                if not ProductCatalogService.reserve_inventory(product_id, quantity):
                    raise ValueError(f"Failed to reserve inventory for product {product_id}")
                
                reserved_items.append({"product_id": product_id, "quantity": quantity})
            
            return reserved_items
            
        except Exception as e:
            # Release any items that were successfully reserved
            for reserved_item in reserved_items:
                ProductCatalogService.release_inventory(
                    reserved_item["product_id"], 
                    reserved_item["quantity"]
                )
            raise
    
    @classmethod
    def _release_inventory(cls, reserved_items: List[Dict[str, Any]]) -> None:
        """Compensation: Release reserved inventory."""
        for item in reserved_items:
            ProductCatalogService.release_inventory(item["product_id"], item["quantity"])
    
    @classmethod
    def _create_order_record(cls, user_id: int, items: List[Dict[str, Any]]) -> int:
        """Create order record."""
        order = OrderOrchestrationService.create_order(user_id, items, "user@example.com")
        return order.id
    
    @classmethod
    def _delete_order_record(cls, order_id: int) -> None:
        """Compensation: Delete order record."""
        OrderOrchestrationService.cancel_order(order_id, "Saga compensation")
    
    @classmethod
    def _process_payment_step(cls, saga_id: str, payment_method: str) -> str:
        """Process payment for the saga."""
        # Get order from previous step
        steps = cls._active_sagas[saga_id]
        order_id = steps[1].result  # Order ID from create_order step
        order = OrderOrchestrationService.get_order(order_id)
        
        payment_result = PaymentService.process_payment(order_id, order.total_amount, payment_method)
        
        if payment_result["status"] != "completed":
            raise ValueError("Payment processing failed")
        
        return payment_result["id"]
    
    @classmethod
    def _refund_payment(cls, transaction_id: str) -> None:
        """Compensation: Refund payment."""
        # In real implementation, would call payment service to refund
        print(f"Refunding payment transaction: {transaction_id}")
    
    @classmethod
    def _send_confirmation_step(cls, saga_id: str) -> bool:
        """Send order confirmation."""
        steps = cls._active_sagas[saga_id]
        order_id = steps[1].result
        order = OrderOrchestrationService.get_order(order_id)
        
        NotificationService.send_order_confirmation(order, "user@example.com")
        return True
    
    @classmethod
    def _send_cancellation_notification(cls, saga_id: str) -> None:
        """Compensation: Send cancellation notification."""
        print(f"Sending cancellation notification for saga: {saga_id}")
    
    @classmethod
    @guarded
    def get_saga_status(cls, saga_id: str) -> Optional[Dict[str, Any]]:
        """Get status of active saga."""
        if saga_id not in cls._active_sagas:
            return None
        
        steps = cls._active_sagas[saga_id]
        return {
            "saga_id": saga_id,
            "steps": [
                {
                    "name": step.name,
                    "status": step.status.value,
                    "error": step.error
                }
                for step in steps
            ]
        }
```

## 🚀 Usage Examples

### Basic Order Workflow

```python
# main.py
from services.order_orchestrator import OrderOrchestrationService
from services.order_queries import OrderQueryService
from services.order_saga import OrderSagaService

def main():
    try:
        # Create order using orchestration service
        order_items = [
            {"product_id": 1, "quantity": 2},  # 2 Laptops
            {"product_id": 3, "quantity": 1}   # 1 Headphones
        ]
        
        order = OrderOrchestrationService.create_order(
            user_id=1,
            items=order_items,
            user_email="customer@example.com"
        )
        
        print(f"Order created: {order.id}, Total: ${order.total_amount:.2f}")
        
        # Confirm order with payment
        confirmed_order = OrderOrchestrationService.confirm_order(
            order.id,
            payment_method="credit_card"
        )
        
        print(f"Order confirmed: {confirmed_order.status}")
        
        # Ship the order
        shipped_order = OrderOrchestrationService.ship_order(
            order.id,
            tracking_number="TRK123456789"
        )
        
        print(f"Order shipped: {shipped_order.status}")
        
        # Query order summary
        summary = OrderQueryService.get_order_summary(order.id)
        print(f"Order summary: {summary}")
        
        # Get analytics
        analytics = OrderQueryService.get_order_analytics()
        print(f"Order analytics: {analytics}")
        
    except Exception as e:
        print(f"Error: {e}")

def saga_example():
    """Example using saga pattern for complex workflow."""
    try:
        saga_id = "saga_001"
        order_items = [
            {"product_id": 2, "quantity": 5}  # 5 Books
        ]
        
        result = OrderSagaService.execute_order_creation_saga(
            saga_id=saga_id,
            user_id=2,
            items=order_items,
            payment_method="paypal"
        )
        
        print(f"Saga completed: {result}")
        
    except Exception as e:
        print(f"Saga failed: {e}")

if __name__ == "__main__":
    main()
    saga_example()
```

### API Integration

```python
# api/order_api.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from services.order_orchestrator import OrderOrchestrationService
from services.order_queries import OrderQueryService
from services.order_saga import OrderSagaService

router = APIRouter()

class OrderItemRequest(BaseModel):
    product_id: int
    quantity: int

class CreateOrderRequest(BaseModel):
    items: List[OrderItemRequest]
    payment_method: str

@router.post("/orders")
async def create_order(request: CreateOrderRequest):
    """Create order using saga pattern."""
    try:
        import uuid
        saga_id = str(uuid.uuid4())
        
        result = OrderSagaService.execute_order_creation_saga(
            saga_id=saga_id,
            user_id=1,  # From auth context
            items=[item.dict() for item in request.items],
            payment_method=request.payment_method
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/orders/{order_id}")
async def get_order(order_id: int):
    """Get order summary."""
    summary = OrderQueryService.get_order_summary(order_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Order not found")
    return summary

@router.get("/orders/user/{user_id}")
async def get_user_orders(user_id: int, include_cancelled: bool = False):
    """Get user order history."""
    return OrderQueryService.get_user_order_history(user_id, include_cancelled)

@router.get("/analytics/orders")
async def get_order_analytics():
    """Get order analytics."""
    return OrderQueryService.get_order_analytics()

@router.post("/orders/{order_id}/ship")
async def ship_order(order_id: int, tracking_number: str):
    """Ship an order."""
    try:
        order = OrderOrchestrationService.ship_order(order_id, tracking_number)
        return {"status": order.status.value, "tracking_number": tracking_number}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

## 🎯 Key Patterns Demonstrated

### 1. Service Orchestration
- Complex workflow coordination
- Multi-service operations
- Error handling and rollback
- Audit trail management

### 2. CQRS Pattern
- Separate read and write models
- Optimized query services
- Data denormalization for reads
- Analytics and reporting

### 3. Saga Pattern
- Distributed transaction management
- Compensation actions
- Long-running workflows
- Failure recovery

### 4. Domain-Driven Design
- Domain service separation
- Business logic encapsulation
- Event-driven architecture
- Bounded contexts

### 5. Resilience Patterns
- Inventory management
- Payment processing
- Notification delivery
- Audit logging

This example demonstrates advanced service composition patterns for building complex, resilient applications with proper separation of concerns and fault tolerance.

---

**Phase 6 Complete!** All 9 examples have been created, demonstrating comprehensive patterns for building production-ready applications with **singleton-service**.

Ready to continue with **Phase 7: API Reference** setup?