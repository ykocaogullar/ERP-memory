#!/bin/bash
# Migration script to apply database schema

set -e

echo "=== Database Migration Script ==="

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c '\q' 2>/dev/null; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

echo "PostgreSQL is ready!"

# Apply migrations
echo "Applying migrations..."
for migration in /migrations/*.sql; do
  if [ -f "$migration" ]; then
    echo "Running migration: $(basename $migration)"
    PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -f "$migration"
  fi
done

echo "Migrations completed successfully!"
