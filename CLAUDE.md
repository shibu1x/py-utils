# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python utilities collection for MySQL database operations and AWS S3 integration. Two main utilities:

1. **import_csv_to_mysql**: Imports credit card transaction CSV files (Shift-JIS encoded) into MySQL `credit_histories` table
2. **mysql_backup_to_s3**: Creates MySQL database backups, compresses them, and uploads to AWS S3

## Architecture

### Database Schema

The `credit_histories` table (see `import_csv_to_mysql/output_table.sql`) stores credit card transaction data:
- Transaction details: `used_at`, `store`, `price`, `payment`
- Metadata: `service` (vpass/enavi), `file` (source CSV filename), `card_number`
- Unique constraint on `(used_at, store, price, payment, service, file)` to prevent duplicates

### CSV Import Flow

1. Reads Shift-JIS encoded CSV files from `import_csv_to_mysql/csv_data/`
2. Extracts card numbers from special rows (format: `****-****-****-1234`)
3. Normalizes text to NFKC (converts full-width to half-width)
4. Checks for duplicate imports using `(service, file)` combination
5. Inserts transaction records with deduplication

### Backup Flow

1. Runs `mysqldump` with SSL and single-transaction mode
2. Compresses dump file with gzip
3. Uploads to S3 with `STANDARD_IA` storage class
4. Cleans up local temporary files

## Development Commands

### Build Docker Image (Local)

```bash
# Build for AMD64 and push to private registry
task build

# Build for specific architecture
task amd VERSION=latest
task arm
```

### Run Utilities in Docker

```bash
# Start interactive shell
docker compose run --rm py-utils /bin/bash

# Run CSV import
docker compose run --rm py-utils python import_csv_to_mysql/main.py

# Run MySQL backup
docker compose run --rm py-utils python mysql_backup_to_s3/main.py
```

### Environment Configuration

Required environment variables (configure in `.env`):
```bash
# MySQL Connection
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=your_database

# S3 Configuration (for backup utility)
S3_BUCKET=your-bucket-name
S3_PREFIX=mysql-backups

# Docker Build (for Taskfile)
REGISTRY=cr.quud.net
APT_CACHER=cache.example.com
AMD64_BUILDER=builder-name
REMOTE_HOST=remote.example.com
```

AWS credentials are mounted from `~/.aws` directory in Docker Compose.

## Security Considerations

- `.env` file contains sensitive credentials and must never be committed
- CSV files in `import_csv_to_mysql/csv_data/` may contain personal financial data
- Both are excluded in `.gitignore`
- Use `.env.example` as template for new environments

## Key Implementation Details

### CSV Import

- Encoding: Shift-JIS (Japanese credit card statements)
- Text normalization: NFKC for consistent full-width/half-width handling
- Duplicate prevention: Checks `(service, file)` before processing entire file
- Service types: `vpass` (default), `enavi`

### MySQL Backup

- Uses `--single-transaction` for consistent snapshot without table locks
- SSL enabled with `--ssl-verify-server-cert=0` for flexible cert validation
- Compression: gzip with force flag (`-f`)
- S3 storage class: `STANDARD_IA` (Infrequent Access) for cost optimization
