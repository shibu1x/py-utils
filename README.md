# py-utils

Python utilities for MySQL database operations and AWS S3 integration.

## Features

### 1. CSV to MySQL Importer (`import_csv_to_mysql`)

Import credit card transaction CSV files into MySQL database.

- Supports Shift-JIS encoded CSV files (Japanese credit card statements)
- Automatic duplicate detection
- Text normalization (NFKC)
- Supports multiple credit card services (vpass, enavi)

### 2. MySQL Backup to S3 (`mysql_backup_to_s3`)

Automated MySQL database backup with S3 storage.

- Creates consistent database snapshots using mysqldump
- Automatic gzip compression
- Direct upload to AWS S3
- Cost-optimized storage (S3 Infrequent Access)

## Prerequisites

- Docker and Docker Compose
- AWS credentials configured (for S3 backup)
- MySQL database

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

### CSV Import

1. Place your CSV files in `import_csv_to_mysql/csv_data/`
2. Run the import script:
```bash
docker compose run --rm py-utils python import_csv_to_mysql/main.py
```

### MySQL Backup

Run the backup script:
```bash
docker compose run --rm py-utils python mysql_backup_to_s3/main.py
```

The backup will be uploaded to S3 with the format: `{S3_PREFIX}/{database_name}.sql.gz`

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
docker compose run --rm py-utils /bin/bash
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

- Never commit `.env` file or CSV data files
- `.env` contains sensitive database credentials
- CSV files may contain personal financial information
- Use `.env.example` as a template for new environments

## License

MIT
