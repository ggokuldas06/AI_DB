#!/usr/bin/env bash
set -euo pipefail

# Tear down any existing container + volume, then start fresh
docker compose down -v --remove-orphans 2>/dev/null || true
docker compose up -d

echo "Waiting for Postgres to be ready..."
until docker compose exec -T postgres pg_isready -U aidb_user -d sales_db -q; do
  sleep 1
done

echo "Database is ready."
echo ""
echo "Connection details:"
echo "  Host:     localhost"
echo "  Port:     5432"
echo "  Database: sales_db"
echo "  User:     aidb_user"
echo "  Password: aidb_pass"
echo "  DSN:      postgresql://aidb_user:aidb_pass@localhost:5432/sales_db"
