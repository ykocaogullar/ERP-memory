"""
Domain Query Service

Queries the ERP database (domain schema) and formats results for LLM context.
Provides structured access to business data with entity linking.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
from datetime import datetime, date

from api.utils.database import db
from api.models.domain import Customer, SalesOrder, WorkOrder, Invoice, Payment, Task

logger = logging.getLogger(__name__)


class DomainQueryService:
    """Queries domain database and formats results for LLM context"""
    
    def get_customer_data(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive customer data including related entities"""
        # Get customer basic info
        customer_query = """
            SELECT customer_id, name, industry, notes, created_at
            FROM domain.customers
            WHERE customer_id = %s
        """
        customer = db.execute_query(customer_query, (customer_id,), fetch_one=True)
        if not customer:
            return None
        
        # Get related sales orders
        orders_query = """
            SELECT so_id, so_number, title, status, created_at
            FROM domain.sales_orders
            WHERE customer_id = %s
            ORDER BY created_at DESC
        """
        orders = db.execute_query(orders_query, (customer_id,))
        
        # Get open invoices
        invoices_query = """
            SELECT i.invoice_id, i.invoice_number, i.amount, i.due_date, i.status, i.issued_at, so.so_number
            FROM domain.invoices i
            JOIN domain.sales_orders so ON i.so_id = so.so_id
            WHERE so.customer_id = %s AND i.status = 'open'
            ORDER BY i.due_date ASC
        """
        invoices = db.execute_query(invoices_query, (customer_id,))
        
        # Get open tasks
        tasks_query = """
            SELECT task_id, title, body, status, created_at
            FROM domain.tasks
            WHERE customer_id = %s AND status != 'done'
            ORDER BY created_at DESC
        """
        tasks = db.execute_query(tasks_query, (customer_id,))
        
        # Calculate summary statistics
        total_orders = len(orders)
        open_invoices = len(invoices)
        total_open_amount = sum(float(inv['amount']) for inv in invoices)
        open_tasks = len(tasks)
        
        return {
            'customer': customer,
            'orders': orders,
            'invoices': invoices,
            'tasks': tasks,
            'summary': {
                'total_orders': total_orders,
                'open_invoices': open_invoices,
                'total_open_amount': total_open_amount,
                'open_tasks': open_tasks
            }
        }
    
    def get_sales_order_data(self, so_id: str) -> Optional[Dict[str, Any]]:
        """Get sales order with related work orders and invoices"""
        # Get sales order
        so_query = """
            SELECT so.so_id, so.so_number, so.title, so.status, so.created_at,
                   c.customer_id, c.name as customer_name, c.industry
            FROM domain.sales_orders so
            JOIN domain.customers c ON so.customer_id = c.customer_id
            WHERE so.so_id = %s
        """
        sales_order = db.execute_query(so_query, (so_id,), fetch_one=True)
        if not sales_order:
            return None
        
        # Get work orders
        wo_query = """
            SELECT wo_id, description, status, technician, scheduled_for
            FROM domain.work_orders
            WHERE so_id = %s
            ORDER BY scheduled_for ASC
        """
        work_orders = db.execute_query(wo_query, (so_id,))
        
        # Get invoices
        inv_query = """
            SELECT invoice_id, invoice_number, amount, due_date, status, issued_at
            FROM domain.invoices
            WHERE so_id = %s
            ORDER BY issued_at DESC
        """
        invoices = db.execute_query(inv_query, (so_id,))
        
        # Get payments for invoices
        payments = []
        if invoices:
            invoice_ids = [inv['invoice_id'] for inv in invoices]
            pay_query = """
                SELECT p.payment_id, p.invoice_id, p.amount, p.method, p.paid_at, i.invoice_number
                FROM domain.payments p
                JOIN domain.invoices i ON p.invoice_id = i.invoice_id
                WHERE p.invoice_id = ANY(%s)
                ORDER BY p.paid_at DESC
            """
            payments = db.execute_query(pay_query, (invoice_ids,))
        
        return {
            'sales_order': sales_order,
            'work_orders': work_orders,
            'invoices': invoices,
            'payments': payments
        }
    
    def get_invoice_data(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """Get invoice with payment history and related order info"""
        # Get invoice with order and customer info
        inv_query = """
            SELECT i.invoice_id, i.invoice_number, i.amount, i.due_date, i.status, i.issued_at,
                   so.so_number, so.title as order_title,
                   c.customer_id, c.name as customer_name
            FROM domain.invoices i
            JOIN domain.sales_orders so ON i.so_id = so.so_id
            JOIN domain.customers c ON so.customer_id = c.customer_id
            WHERE i.invoice_id = %s
        """
        invoice = db.execute_query(inv_query, (invoice_id,), fetch_one=True)
        if not invoice:
            return None
        
        # Get payments
        pay_query = """
            SELECT payment_id, amount, method, paid_at
            FROM domain.payments
            WHERE invoice_id = %s
            ORDER BY paid_at DESC
        """
        payments = db.execute_query(pay_query, (invoice_id,))
        
        # Calculate payment summary
        total_paid = sum(float(p['amount']) for p in payments)
        balance = float(invoice['amount']) - total_paid
        is_overdue = invoice['due_date'] < date.today() and invoice['status'] == 'open'
        
        return {
            'invoice': invoice,
            'payments': payments,
            'summary': {
                'total_amount': float(invoice['amount']),
                'total_paid': total_paid,
                'balance': balance,
                'is_overdue': is_overdue,
                'days_overdue': (date.today() - invoice['due_date']).days if is_overdue else 0
            }
        }
    
    def search_customers(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search customers by name using fuzzy matching"""
        search_query = """
            SELECT customer_id, name, industry, notes,
                   similarity(name, %s) as score
            FROM domain.customers
            WHERE similarity(name, %s) > 0.3
            ORDER BY score DESC
            LIMIT %s
        """
        return db.execute_query(search_query, (query, query, limit))
    
    def get_overdue_invoices(self, days_threshold: int = 0) -> List[Dict[str, Any]]:
        """Get invoices that are overdue by specified days"""
        query = """
            SELECT i.invoice_id, i.invoice_number, i.amount, i.due_date, i.issued_at,
                   c.name as customer_name, so.so_number,
                   (CURRENT_DATE - i.due_date) as days_overdue
            FROM domain.invoices i
            JOIN domain.sales_orders so ON i.so_id = so.so_id
            JOIN domain.customers c ON so.customer_id = c.customer_id
            WHERE i.status = 'open' 
            AND i.due_date < CURRENT_DATE - INTERVAL '%s days'
            ORDER BY days_overdue DESC
        """
        return db.execute_query(query, (days_threshold,))
    
    def get_work_orders_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get work orders by status with related order info"""
        query = """
            SELECT wo.wo_id, wo.description, wo.status, wo.technician, wo.scheduled_for,
                   so.so_number, so.title as order_title,
                   c.name as customer_name
            FROM domain.work_orders wo
            JOIN domain.sales_orders so ON wo.so_id = so.so_id
            JOIN domain.customers c ON so.customer_id = c.customer_id
            WHERE wo.status = %s
            ORDER BY wo.scheduled_for ASC
        """
        return db.execute_query(query, (status,))
    
    def get_tasks_by_customer(self, customer_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get tasks for a customer, optionally filtered by status"""
        if status:
            query = """
                SELECT task_id, title, body, status, created_at
                FROM domain.tasks
                WHERE customer_id = %s AND status = %s
                ORDER BY created_at DESC
            """
            return db.execute_query(query, (customer_id, status))
        else:
            query = """
                SELECT task_id, title, body, status, created_at
                FROM domain.tasks
                WHERE customer_id = %s
                ORDER BY created_at DESC
            """
            return db.execute_query(query, (customer_id,))
    
    def get_customer_financial_summary(self, customer_id: str) -> Dict[str, Any]:
        """Get comprehensive financial summary for a customer"""
        # Get all invoices
        invoices_query = """
            SELECT i.invoice_id, i.invoice_number, i.amount, i.due_date, i.status, i.issued_at,
                   so.so_number
            FROM domain.invoices i
            JOIN domain.sales_orders so ON i.so_id = so.so_id
            WHERE so.customer_id = %s
            ORDER BY i.issued_at DESC
        """
        invoices = db.execute_query(invoices_query, (customer_id,))
        
        # Get all payments
        payments_query = """
            SELECT p.amount, p.paid_at, i.invoice_number
            FROM domain.payments p
            JOIN domain.invoices i ON p.invoice_id = i.invoice_id
            JOIN domain.sales_orders so ON i.so_id = so.so_id
            WHERE so.customer_id = %s
            ORDER BY p.paid_at DESC
        """
        payments = db.execute_query(payments_query, (customer_id,))
        
        # Calculate summary
        total_invoiced = sum(float(inv['amount']) for inv in invoices)
        total_paid = sum(float(p['amount']) for p in payments)
        open_invoices = [inv for inv in invoices if inv['status'] == 'open']
        total_open = sum(float(inv['amount']) for inv in open_invoices)
        
        # Overdue calculation
        overdue_invoices = [inv for inv in open_invoices if inv['due_date'] < date.today()]
        total_overdue = sum(float(inv['amount']) for inv in overdue_invoices)
        
        return {
            'total_invoiced': total_invoiced,
            'total_paid': total_paid,
            'total_open': total_open,
            'total_overdue': total_overdue,
            'invoice_count': len(invoices),
            'open_invoice_count': len(open_invoices),
            'overdue_invoice_count': len(overdue_invoices),
            'payment_count': len(payments)
        }
    
    def format_for_llm_context(self, data: Dict[str, Any], context_type: str) -> str:
        """Format domain data for LLM context as semantic triples"""
        if context_type == 'customer':
            return self._format_customer_context(data)
        elif context_type == 'sales_order':
            return self._format_sales_order_context(data)
        elif context_type == 'invoice':
            return self._format_invoice_context(data)
        else:
            return str(data)
    
    def _format_customer_context(self, data: Dict[str, Any]) -> str:
        """Format customer data as semantic triples"""
        customer = data['customer']
        summary = data['summary']
        
        context_parts = [
            f"=== Customer: {customer['name']} ===",
            f"• (Customer, industry, {customer['industry'] or 'Unknown'})",
            f"• (Customer, total_orders, {summary['total_orders']})",
            f"• (Customer, open_invoices, {summary['open_invoices']})",
            f"• (Customer, total_open_amount, ${summary['total_open_amount']:.2f})",
            f"• (Customer, open_tasks, {summary['open_tasks']})"
        ]
        
        # Add open invoices
        if data['invoices']:
            context_parts.append("\nOpen Invoices:")
            for inv in data['invoices']:
                context_parts.append(f"• ({inv['invoice_number']}, amount, ${inv['amount']})")
                context_parts.append(f"• ({inv['invoice_number']}, due_date, {inv['due_date']})")
                context_parts.append(f"• ({inv['invoice_number']}, status, {inv['status']})")
        
        # Add recent orders
        if data['orders']:
            context_parts.append("\nRecent Orders:")
            for order in data['orders'][:3]:  # Limit to 3 most recent
                context_parts.append(f"• ({order['so_number']}, status, {order['status']})")
                context_parts.append(f"• ({order['so_number']}, title, {order['title']})")
        
        return "\n".join(context_parts)
    
    def _format_sales_order_context(self, data: Dict[str, Any]) -> str:
        """Format sales order data as semantic triples"""
        so = data['sales_order']
        
        context_parts = [
            f"=== Sales Order: {so['so_number']} ===",
            f"• (Order, customer, {so['customer_name']})",
            f"• (Order, status, {so['status']})",
            f"• (Order, title, {so['title']})"
        ]
        
        # Add work orders
        if data['work_orders']:
            context_parts.append("\nWork Orders:")
            for wo in data['work_orders']:
                context_parts.append(f"• (WorkOrder, status, {wo['status']})")
                if wo['technician']:
                    context_parts.append(f"• (WorkOrder, technician, {wo['technician']})")
                if wo['scheduled_for']:
                    context_parts.append(f"• (WorkOrder, scheduled_for, {wo['scheduled_for']})")
        
        # Add invoices
        if data['invoices']:
            context_parts.append("\nInvoices:")
            for inv in data['invoices']:
                context_parts.append(f"• ({inv['invoice_number']}, amount, ${inv['amount']})")
                context_parts.append(f"• ({inv['invoice_number']}, status, {inv['status']})")
        
        return "\n".join(context_parts)
    
    def _format_invoice_context(self, data: Dict[str, Any]) -> str:
        """Format invoice data as semantic triples"""
        invoice = data['invoice']
        summary = data['summary']
        
        context_parts = [
            f"=== Invoice: {invoice['invoice_number']} ===",
            f"• (Invoice, customer, {invoice['customer_name']})",
            f"• (Invoice, order, {invoice['so_number']})",
            f"• (Invoice, amount, ${summary['total_amount']:.2f})",
            f"• (Invoice, paid_amount, ${summary['total_paid']:.2f})",
            f"• (Invoice, balance, ${summary['balance']:.2f})",
            f"• (Invoice, status, {invoice['status']})",
            f"• (Invoice, due_date, {invoice['due_date']})"
        ]
        
        if summary['is_overdue']:
            context_parts.append(f"• (Invoice, days_overdue, {summary['days_overdue']})")
        
        # Add payments
        if data['payments']:
            context_parts.append("\nPayments:")
            for payment in data['payments']:
                context_parts.append(f"• (Payment, amount, ${payment['amount']})")
                context_parts.append(f"• (Payment, method, {payment['method'] or 'Unknown'})")
                context_parts.append(f"• (Payment, paid_at, {payment['paid_at']})")
        
        return "\n".join(context_parts)


# Singleton instance
_domain_query_service = None

def get_domain_query_service() -> DomainQueryService:
    """Get singleton instance of DomainQueryService"""
    global _domain_query_service
    if _domain_query_service is None:
        _domain_query_service = DomainQueryService()
    return _domain_query_service
