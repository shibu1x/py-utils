# py-utils

Python utilities for file processing, MySQL database operations, and AWS S3 integration.

## Features

### 1. ZIP to CBZ Converter (`zip_to_cbz`)

Convert ZIP archives to CBZ (comic book) format with sequential image numbering.

- Extracts images from ZIP files
- Renames images to sequential 3-digit numbers (001.jpg, 002.jpg, etc.)
- Supports multiple image formats (jpg, png, gif, bmp, webp)
- Automatic cleanup of temporary files

### 2. CSV to MySQL Importer (`import_csv_to_mysql`)

Import credit card transaction CSV files into MySQL database.

- Supports Shift-JIS encoded CSV files (Japanese credit card statements)
- Automatic duplicate detection
- Text normalization (NFKC)
- Supports multiple credit card services (vpass, enavi)

### 3. MySQL Backup to S3 (`mysql_backup_to_s3`)

Automated MySQL database backup with S3 storage.

- Creates consistent database snapshots using mysqldump
- Automatic gzip compression
- Direct upload to AWS S3
- Cost-optimized storage (S3 Infrequent Access)

## Prerequisites

- Docker and Docker Compose
- AWS credentials configured (for mysql_backup_to_s3 only)
- MySQL database (for import_csv_to_mysql and mysql_backup_to_s3 only)

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd py-utils
```

2. Copy the example environment file and configure:
```bash
cp .env.example .env
# Edit .env with your database and S3 credentials
```

3. Build the Docker image:
```bash
task build
```

Or use Docker Compose:
```bash
docker compose build
```

## Usage

### ZIP to CBZ Conversion

1. Place your ZIP files in `zip_to_cbz/data/src/`
2. Run the conversion script:
```bash
docker compose run --rm py-utils zip_to_cbz/main.py
```
3. Converted CBZ files will be in `zip_to_cbz/data/dest/`

### CSV Import

1. Place your CSV files in `import_csv_to_mysql/csv_data/`
2. Run the import script:
```bash
docker compose run --rm py-utils import_csv_to_mysql/main.py
```

### MySQL Backup

Run the backup script:
```bash
docker compose run --rm py-utils mysql_backup_to_s3/main.py
```

The backup will be uploaded to S3 with the format: `{S3_PREFIX}/{database_name}.sql.gz`

### Note on Docker Commands

The Docker image uses an entrypoint script that automatically passes arguments to Python. You can run scripts without explicitly specifying `python`.

## Environment Variables

Create a `.env` file with the following variables:

```bash
# MySQL Database Configuration
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password_here
DB_NAME=your_database_name

# AWS S3 Configuration
S3_BUCKET=your-s3-bucket-name
S3_PREFIX=mysql-backups

# Backup Configuration (optional)
BACKUP_DIR=/tmp
```

## Database Schema

The CSV importer requires a `credit_histories` table. See `import_csv_to_mysql/output_table.sql` for the schema definition.

Create the table:
```bash
mysql -u root -p your_database < import_csv_to_mysql/output_table.sql
```

## Development

### Run Interactive Shell

```bash
docker compose run --rm py-utils
```

### Build with Taskfile

```bash
# Build and push to registry
task build

# Build specific architecture
task amd VERSION=latest
task arm
```

## Security Notes

- Never commit `.env` file or data files (CSV, ZIP, CBZ)
- `.env` contains sensitive database credentials
- CSV files may contain personal financial information
- ZIP/CBZ files may contain copyrighted content
- All sensitive data files are excluded in `.gitignore`
- Use `.env.example` as a template for new environments

## License

MIT
