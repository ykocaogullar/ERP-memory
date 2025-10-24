-- Seed data for ERP Memory System
-- This file populates the domain schema with sample data for testing

-- Customers
INSERT INTO domain.customers (customer_id, name, industry, notes) VALUES
('550e8400-e29b-41d4-a716-446655440001', 'Gai Media', 'Entertainment', 'Album fulfillment and distribution'),
('550e8400-e29b-41d4-a716-446655440002', 'PC Boiler', 'Industrial', 'On-site repair services'),
('550e8400-e29b-41d4-a716-446655440003', 'TC Boiler', 'Industrial', 'Equipment maintenance')
ON CONFLICT (customer_id) DO NOTHING;

-- Sales Orders
INSERT INTO domain.sales_orders (so_id, customer_id, so_number, title, status, created_at) VALUES
('550e8400-e29b-41d4-a716-446655440011', '550e8400-e29b-41d4-a716-446655440001', 'SO-1001', 'Album Fulfillment Q3', 'in_fulfillment', '2025-09-01'),
('550e8400-e29b-41d4-a716-446655440012', '550e8400-e29b-41d4-a716-446655440002', 'SO-2002', 'On-site valve repair', 'approved', '2025-09-15')
ON CONFLICT (so_number) DO NOTHING;

-- Work Orders
INSERT INTO domain.work_orders (wo_id, so_id, description, status, technician, scheduled_for) VALUES
('550e8400-e29b-41d4-a716-446655440021', '550e8400-e29b-41d4-a716-446655440011', 'Pick-pack albums for shipping', 'queued', 'Alex', '2025-09-22'),
('550e8400-e29b-41d4-a716-446655440022', '550e8400-e29b-41d4-a716-446655440012', 'Replace boiler valve', 'blocked', 'Jordan', '2025-09-25')
ON CONFLICT DO NOTHING;

-- Invoices
INSERT INTO domain.invoices (invoice_id, so_id, invoice_number, amount, due_date, status, issued_at) VALUES
('550e8400-e29b-41d4-a716-446655440031', '550e8400-e29b-41d4-a716-446655440011', 'INV-1009', 1200.00, '2025-09-30', 'open', '2025-09-01'),
('550e8400-e29b-41d4-a716-446655440032', '550e8400-e29b-41d4-a716-446655440012', 'INV-2201', 850.00, '2025-10-15', 'open', '2025-09-15')
ON CONFLICT (invoice_number) DO NOTHING;

-- Payments (partial payment for INV-2201)
INSERT INTO domain.payments (payment_id, invoice_id, amount, method, paid_at) VALUES
('550e8400-e29b-41d4-a716-446655440041', '550e8400-e29b-41d4-a716-446655440032', 400.00, 'ACH', '2025-10-01')
ON CONFLICT DO NOTHING;

-- Tasks
INSERT INTO domain.tasks (task_id, customer_id, title, body, status, created_at) VALUES
('550e8400-e29b-41d4-a716-446655440051', '550e8400-e29b-41d4-a716-446655440001', 'Investigate shipping SLA for Gai Media', 'Check if current shipping provider meets 3-day SLA', 'todo', now() - interval '10 days'),
('550e8400-e29b-41d4-a716-446655440052', '550e8400-e29b-41d4-a716-446655440002', 'Follow up on PC Boiler repair schedule', 'Confirm technician availability for valve replacement', 'doing', now() - interval '2 days')
ON CONFLICT DO NOTHING;

-- Print summary
DO $$
DECLARE
    customer_count INT;
    order_count INT;
    invoice_count INT;
BEGIN
    SELECT COUNT(*) INTO customer_count FROM domain.customers;
    SELECT COUNT(*) INTO order_count FROM domain.sales_orders;
    SELECT COUNT(*) INTO invoice_count FROM domain.invoices;
    
    RAISE NOTICE '=== Seed Data Summary ===';
    RAISE NOTICE 'Customers: %', customer_count;
    RAISE NOTICE 'Sales Orders: %', order_count;
    RAISE NOTICE 'Invoices: %', invoice_count;
    RAISE NOTICE '========================';
END $$;
