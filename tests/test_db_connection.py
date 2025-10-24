#!/usr/bin/env python3
"""Quick test to verify database connectivity and schema"""

import psycopg2
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Database connection parameters
DB_PARAMS = {
    'host': 'localhost',  # Using localhost since we're connecting from host
    'port': 5432,
    'database': os.getenv('DB_NAME', 'erp_db'),
    'user': os.getenv('DB_USER', 'erp_user'),
    'password': os.getenv('DB_PASSWORD', 'erp_password')
}

def test_connection():
    """Test database connection and verify schema"""
    print("=" * 60)
    print("Database Connection Test")
    print("=" * 60)
    
    try:
        # Connect to database
        conn = psycopg2.connect(**DB_PARAMS)
        cursor = conn.cursor()
        print("✅ Successfully connected to database!")
        
        # Test 1: Check PostgreSQL version
        cursor.execute("SELECT version();")
        pg_version = cursor.fetchone()[0]
        print(f"\n📊 PostgreSQL Version:\n   {pg_version[:80]}...")
        
        # Test 2: Check extensions
        cursor.execute("""
            SELECT extname, extversion 
            FROM pg_extension 
            WHERE extname IN ('vector', 'pg_trgm')
            ORDER BY extname;
        """)
        extensions = cursor.fetchall()
        print(f"\n🔌 Extensions:")
        for ext_name, ext_version in extensions:
            print(f"   ✅ {ext_name}: v{ext_version}")
        
        # Test 3: Check domain schema tables
        cursor.execute("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'domain' 
            ORDER BY tablename;
        """)
        domain_tables = cursor.fetchall()
        print(f"\n📁 Domain Schema Tables ({len(domain_tables)}):")
        for (table,) in domain_tables:
            print(f"   ✅ {table}")
        
        # Test 4: Check app schema tables
        cursor.execute("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'app' 
            ORDER BY tablename;
        """)
        app_tables = cursor.fetchall()
        print(f"\n📁 App Schema Tables ({len(app_tables)}):")
        for (table,) in app_tables:
            print(f"   ✅ {table}")
        
        # Test 5: Check seed data
        cursor.execute("SELECT COUNT(*) FROM domain.customers;")
        customer_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM domain.sales_orders;")
        order_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM domain.invoices;")
        invoice_count = cursor.fetchone()[0]
        
        print(f"\n📊 Seed Data:")
        print(f"   ✅ Customers: {customer_count}")
        print(f"   ✅ Sales Orders: {order_count}")
        print(f"   ✅ Invoices: {invoice_count}")
        
        # Test 6: Sample data query
        cursor.execute("""
            SELECT c.name, so.so_number, so.status, i.invoice_number, i.amount, i.status as invoice_status
            FROM domain.customers c
            JOIN domain.sales_orders so ON c.customer_id = so.customer_id
            JOIN domain.invoices i ON so.so_id = i.so_id
            ORDER BY c.name;
        """)
        orders = cursor.fetchall()
        print(f"\n📋 Sample Order Data:")
        for customer, so_num, so_status, inv_num, amount, inv_status in orders:
            print(f"   • {customer}: {so_num} ({so_status}) → {inv_num} ${amount:.2f} ({inv_status})")
        
        # Test 7: Check vector column
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'app' 
            AND table_name IN ('entities', 'memories', 'entity_relationships')
            AND column_name LIKE '%embedding%'
            ORDER BY table_name, column_name;
        """)
        vector_columns = cursor.fetchall()
        print(f"\n🎯 Vector Columns:")
        for col_name, data_type in vector_columns:
            print(f"   ✅ {col_name} ({data_type})")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("=" * 60)
        return False

if __name__ == "__main__":
    test_connection()
