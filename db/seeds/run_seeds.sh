#!/bin/bash
# Seed script to populate database with sample data

set -e

echo "=== Database Seed Script ==="

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c '\q' 2>/dev/null; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

echo "PostgreSQL is ready!"

# Apply seed data
echo "Seeding database..."
for seed in /seeds/*.sql; do
  if [ -f "$seed" ]; then
    echo "Running seed: $(basename $seed)"
    PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -f "$seed"
  fi
done

echo "Seeding completed successfully!"
