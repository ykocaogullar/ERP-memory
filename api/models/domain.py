"""
Domain Models - Pydantic models for ERP domain entities.

These models represent the core business entities in the ERP system
(customers, orders, invoices, etc.) and are used for data validation
and serialization when interacting with the domain schema.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# Enums
# ============================================================================

class OrderStatus(str, Enum):
    """Status values for sales orders."""
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class InvoiceStatus(str, Enum):
    """Status values for invoices."""
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class WorkOrderStatus(str, Enum):
    """Status values for work orders."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskStatus(str, Enum):
    """Status values for tasks."""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


# ============================================================================
# Domain Models
# ============================================================================

class Customer(BaseModel):
    """Customer entity from domain.customers table."""
    
    model_config = ConfigDict(from_attributes=True)
    
    customer_id: UUID
    name: str
    industry: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class SalesOrder(BaseModel):
    """Sales order entity from domain.sales_orders table."""
    
    model_config = ConfigDict(from_attributes=True)
    
    order_id: UUID
    customer_id: UUID
    order_number: str
    order_date: datetime
    status: OrderStatus
    total_amount: Decimal
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class WorkOrder(BaseModel):
    """Work order entity from domain.work_orders table."""
    
    model_config = ConfigDict(from_attributes=True)
    
    work_order_id: UUID
    sales_order_id: UUID
    work_order_number: str
    description: str
    status: WorkOrderStatus
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class Invoice(BaseModel):
    """Invoice entity from domain.invoices table."""
    
    model_config = ConfigDict(from_attributes=True)
    
    invoice_id: UUID
    sales_order_id: UUID
    invoice_number: str
    invoice_date: datetime
    due_date: datetime
    status: InvoiceStatus
    total_amount: Decimal
    amount_paid: Decimal = Decimal("0.00")
    created_at: datetime
    updated_at: datetime


class Payment(BaseModel):
    """Payment entity from domain.payments table."""
    
    model_config = ConfigDict(from_attributes=True)
    
    payment_id: UUID
    invoice_id: UUID
    payment_date: datetime
    amount: Decimal
    payment_method: Optional[str] = None
    reference_number: Optional[str] = None
    created_at: datetime


class Task(BaseModel):
    """Task entity from domain.tasks table."""
    
    model_config = ConfigDict(from_attributes=True)
    
    task_id: UUID
    work_order_id: Optional[UUID] = None
    title: str
    description: Optional[str] = None
    status: TaskStatus
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
