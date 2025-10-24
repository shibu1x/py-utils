# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python utilities collection for file processing, MySQL database operations, and AWS S3 integration. Three standalone utilities:

1. **zip_to_cbz**: Converts ZIP archives to CBZ (comic book) format with sequential image numbering
2. **import_csv_to_mysql**: Imports credit card transaction CSV files (Shift-JIS encoded) into MySQL `credit_histories` table
3. **mysql_backup_to_s3**: Creates MySQL database backups, compresses them, and uploads to AWS S3

## Architecture

### Docker Entrypoint Pattern

The Docker image uses `entrypoint.sh` to handle execution:
- With arguments: passes them directly to `python` (e.g., `docker compose run --rm py-utils import_csv_to_mysql/main.py`)
- Without arguments: starts an interactive bash shell
- Current directory (`.`) is mounted at `/app` in the container for development

### Database Schema

The `credit_histories` table (see `import_csv_to_mysql/output_table.sql`):
- Columns: `id`, `used_at`, `store`, `price`, `payment`, `note`, `service` (vpass/enavi), `file`, `created_at`, `updated_at`
- Primary key: `id` (bigint unsigned auto-increment)
- No explicit unique constraint in schema, but duplicate prevention is handled in application logic by checking `(service, file)` combination

### ZIP to CBZ Conversion Flow

1. Reads ZIP files from `zip_to_cbz/data/src/`
2. Extracts to temporary directory (`zip_to_cbz/data/temp/`)
3. Recursively finds all images and renames to sequential 3-digit numbers (001.jpg, 002.jpg, etc.)
4. Creates CBZ file (ZIP with .cbz extension) in `zip_to_cbz/data/dest/`
5. CBZ filename: Uses the name of the directory containing the images (not the ZIP filename)
6. Cleans up temp directory completely at start and end of processing

**Important**: The temp directory (`zip_to_cbz/data/temp/`) is deleted both before and after processing to ensure clean state.

### CSV Import Flow

1. Reads Shift-JIS encoded CSV files from `import_csv_to_mysql/csv_data/`
2. Extracts card numbers from special rows (format: `****-****-****-1234`)
3. Normalizes text to NFKC (converts full-width to half-width characters)
4. Checks for duplicate imports using `(service, file)` combination - skips entire file if already imported
5. Inserts transaction records with `created_at`/`updated_at` timestamps

### MySQL Backup Flow

1. Runs `mysqldump` with `--single-transaction`, `--quick`, `--lock-tables=false`, SSL enabled
2. Compresses dump file with `gzip -f`
3. Uploads to S3 with `STANDARD_IA` storage class
4. Cleans up local compressed file (not the uncompressed dump, as it's already compressed in place)

## Development Commands

### Build Docker Image

```bash
# Build for AMD64 and push to private registry (defined in .env)
task build

# Build specific architecture
task amd VERSION=latest
task arm

# Build development image using Dockerfile.dev
task dev
```

### Run Utilities

```bash
# Start interactive shell in production image
docker compose run --rm py-utils

# Start interactive shell in dev image
docker compose run --rm dev

# Run utilities (entrypoint automatically passes to python)
docker compose run --rm py-utils zip_to_cbz/main.py
docker compose run --rm py-utils import_csv_to_mysql/main.py
docker compose run --rm py-utils mysql_backup_to_s3/main.py
```

### Local Development

The compose.yaml defines two services:
- `py-utils`: Production image (not defined in compose.yaml, assumed to be built separately)
- `dev`: Development image using `${REGISTRY}/py-utils:dev` with current directory mounted

### Environment Configuration

Required environment variables (configure in `.env`):

```bash
# MySQL Connection
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password_here
DB_NAME=your_database_name

# S3 Configuration (for backup utility)
S3_BUCKET=your-s3-bucket-name
S3_PREFIX=mysql-backups
BACKUP_DIR=/tmp

# Docker Build (for Taskfile)
REGISTRY=registry.example.com
APT_CACHER=cache.example.com
AMD64_BUILDER=builder-name
REMOTE_HOST=remote.example.com
```

AWS credentials are mounted from `~/.aws` directory in Docker Compose.

## GitHub Actions

The `.github/workflows/docker-build-push.yml` workflow:
- Triggers: Manual (`workflow_dispatch`) or push to `main` branch with changes to `Dockerfile`, `**/*.py`, `requirements.txt`, or `.dockerignore`
- Builds multi-platform image (linux/amd64, linux/arm64)
- Pushes to GitHub Container Registry (ghcr.io) with tag `latest`
- Uses GitHub Actions cache for faster builds

## Key Implementation Details

### ZIP to CBZ Conversion

- Supported image formats: jpg, jpeg, png, gif, bmp, webp (case-insensitive)
- Uses recursive search (`rglob`) to find images in subdirectories
- Numbering format: 3-digit zero-padded (001, 002, 003, etc.)
- CBZ naming: Uses `image_dir.name` (directory containing the first image found)
- Creates intermediate `{zip_stem}_numbered` directory for renamed files
- Both extracted directory and numbered directory are cleaned up after processing

### CSV Import

- Encoding: Shift-JIS (Japanese credit card statements)
- Text normalization: NFKC for `store` and `note` fields
- Card number detection: Looks for rows with `-` and `*` characters in second column
- Duplicate prevention: Queries database for existing `(service, file)` before processing
- Service type: Currently hardcoded to `'vpass'` in main()
- Date format: `%Y/%m/%d`

### MySQL Backup

- mysqldump flags: `--single-transaction`, `--quick`, `--lock-tables=false`, `--ssl`, `--ssl-verify-server-cert=0`
- Compression: `gzip -f` (force overwrite if file exists)
- S3 upload: Uses `boto3.client("s3").upload_file()` with `StorageClass: STANDARD_IA`
- Cleanup: Only removes compressed file, not uncompressed (since gzip replaces original)
- Validation: Exits with error if `DB_PASSWORD` or `S3_BUCKET` not set
