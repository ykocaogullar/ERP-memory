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
    APPROVED = "approved"
    IN_FULFILLMENT = "in_fulfillment"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"


class InvoiceStatus(str, Enum):
    """Status values for invoices."""
    OPEN = "open"
    PAID = "paid"
    VOID = "void"


class WorkOrderStatus(str, Enum):
    """Status values for work orders."""
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"


class TaskStatus(str, Enum):
    """Status values for tasks."""
    TODO = "todo"
    DOING = "doing"
    DONE = "done"


# ============================================================================
# Domain Models
# ============================================================================

class Customer(BaseModel):
    """Customer entity from domain.customers table."""
    
    model_config = ConfigDict(from_attributes=True)
    
    customer_id: UUID
    name: str
    industry: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime


class SalesOrder(BaseModel):
    """Sales order entity from domain.sales_orders table."""
    
    model_config = ConfigDict(from_attributes=True)
    
    so_id: UUID
    customer_id: UUID
    so_number: str
    title: str
    status: OrderStatus
    created_at: datetime


class WorkOrder(BaseModel):
    """Work order entity from domain.work_orders table."""
    
    model_config = ConfigDict(from_attributes=True)
    
    wo_id: UUID
    so_id: UUID
    description: Optional[str] = None
    status: WorkOrderStatus
    technician: Optional[str] = None
    scheduled_for: Optional[datetime] = None


class Invoice(BaseModel):
    """Invoice entity from domain.invoices table."""
    
    model_config = ConfigDict(from_attributes=True)
    
    invoice_id: UUID
    so_id: UUID
    invoice_number: str
    amount: Decimal
    due_date: datetime
    status: InvoiceStatus
    issued_at: datetime


class Payment(BaseModel):
    """Payment entity from domain.payments table."""
    
    model_config = ConfigDict(from_attributes=True)
    
    payment_id: UUID
    invoice_id: UUID
    amount: Decimal
    method: Optional[str] = None
    paid_at: datetime


class Task(BaseModel):
    """Task entity from domain.tasks table."""
    
    model_config = ConfigDict(from_attributes=True)
    
    task_id: UUID
    customer_id: Optional[UUID] = None
    title: str
    body: Optional[str] = None
    status: TaskStatus
    created_at: datetime
