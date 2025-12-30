# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python utilities collection for file processing, MySQL database operations, AWS S3 integration, and Chromecast TTS. Three standalone utilities located in the `app/` directory:

1. **import_csv_to_mysql**: Imports credit card transaction CSV files (Shift-JIS encoded) into MySQL `credit_histories` table
2. **export_mysql_to_s3**: Creates MySQL database backups, compresses them, and uploads to AWS S3
3. **say_chromecast**: Generates TTS audio files and plays them on Google Nest Mini via Chromecast

## Architecture

### Docker Entrypoint Pattern

The Docker image uses `app/entrypoint.sh` to handle execution:
- With arguments: passes them directly to `python` (e.g., `docker compose run --rm py-utils import_csv_to_mysql/main.py`)
- Without arguments: starts an interactive bash shell
- The `app/` directory is mounted at `/app` in the container for development

### Database Schema

The `credit_histories` table (see `app/import_csv_to_mysql/output_table.sql`):
- Columns: `id`, `used_at`, `store`, `price`, `payment`, `note`, `service` (vpass/enavi), `file`, `created_at`, `updated_at`
- Primary key: `id` (bigint unsigned auto-increment)
- No explicit unique constraint in schema, but duplicate prevention is handled in application logic by checking `(service, file)` combination

### CSV Import Flow

1. Reads Shift-JIS encoded CSV files from `app/import_csv_to_mysql/data/`
2. Extracts card numbers from special rows (format: `****-****-****-1234`)
3. Normalizes text to NFKC (converts full-width to half-width characters)
4. Checks for duplicate imports using `(service, file)` combination - skips entire file if already imported
5. Inserts transaction records with `created_at`/`updated_at` timestamps

### MySQL Backup Flow

1. Runs `mysqldump` with `--single-transaction`, `--quick`, `--lock-tables=false`, SSL enabled
2. Compresses dump file with `gzip -f`
3. Uploads to S3 (no storage class specified - uses bucket default)
4. Cleans up local compressed file (not the uncompressed dump, as it's already compressed in place)

### Chromecast TTS Flow

1. Generates audio file using Google Text-to-Speech (gTTS) from input text
2. Saves MP3 file to `app/say_chromecast/data/` (uses MD5 hash of text as filename)
3. Discovers Chromecast device by friendly name (with optional IP hint for faster discovery)
4. Plays audio file from external HTTP server URL (nginx httpd service serves files from data directory)
5. Audio files are cached by hash - existing files are reused instead of regenerating

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
docker compose run --rm py-utils import_csv_to_mysql/main.py
docker compose run --rm py-utils export_mysql_to_s3/main.py
docker compose run --rm py-utils say_chromecast/main.py "テキストメッセージ"

# Start HTTP server for audio file serving (required for say_chromecast)
docker compose up -d httpd
```

### Local Development

The compose.yaml defines three services:
- `py-utils`: Production image (not defined in compose.yaml, assumed to be built separately)
- `dev`: Development image using `${REGISTRY}/py-utils:dev` with app/ directory mounted
- `httpd`: Nginx server for serving audio files (port 8050), serves files from `app/say_chromecast/data/`

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

# Chromecast TTS Configuration
CHROMECAST_NAME=Room speaker
CHROMECAST_HOST=192.168.0.2
SERVER_URL=http://192.168.0.3:8050

# Docker Build (for Taskfile)
REGISTRY=registry.example.com
APT_CACHER=cache.example.com
AMD64_BUILDER=builder-name
REMOTE_HOST=remote.example.com
```

AWS credentials are mounted from `~/.aws` directory in Docker Compose.

## GitHub Actions

The `.github/workflows/docker-build-push.yml` workflow:
- Triggers: Manual (`workflow_dispatch`) or push to `main` branch with changes to `Dockerfile`, `**/*.py`, `app/requirements.txt`, or `.dockerignore`
- Builds multi-platform image (linux/amd64, linux/arm64)
- Pushes to GitHub Container Registry (ghcr.io) with tag `latest`
- Uses GitHub Actions cache for faster builds

## Key Implementation Details

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
- S3 upload: Uses `boto3.client("s3").upload_file()` (no storage class specified, uses bucket default)
- Cleanup: Only removes compressed file, not uncompressed (since gzip replaces original)
- Validation: Exits with error if `DB_PASSWORD` or `S3_BUCKET` not set

### Chromecast TTS

- Uses gTTS (Google Text-to-Speech) library for audio generation
- File naming: MD5 hash of input text (enables caching of repeated phrases)
- Audio format: MP3 files stored in `app/say_chromecast/data/`
- Script-relative paths: Uses `Path(__file__).parent` to ensure data directory is correctly located
- Chromecast discovery: Uses `pychromecast.get_listed_chromecasts()` with optional known_hosts hint
- External HTTP server required: Chromecast cannot access local files, requires accessible URL
- Language support: Configurable via `--lang` argument (default: `ja` for Japanese)
