#!/usr/bin/env python3
"""
MySQL Database Backup to S3

This script creates a MySQL database backup using mysqldump,
compresses it with gzip, and uploads it to AWS S3.
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import boto3
from botocore.exceptions import ClientError


class MySQLBackupToS3:
    def __init__(
        self,
        db_host: str,
        db_user: str,
        db_password: str,
        db_name: str,
        s3_bucket: str,
        s3_prefix: str = "mysql-backups",
        backup_dir: str = "/tmp",
    ):
        """
        Initialize MySQL backup configuration.

        Args:
            db_host: MySQL host address
            db_user: MySQL username
            db_password: MySQL password
            db_name: Database name to backup
            s3_bucket: S3 bucket name
            s3_prefix: S3 prefix/folder for backups
            backup_dir: Local directory for temporary backup files
        """
        self.db_host = db_host
        self.db_user = db_user
        self.db_password = db_password
        self.db_name = db_name
        self.s3_bucket = s3_bucket
        self.s3_prefix = s3_prefix
        self.backup_dir = Path(backup_dir)
        self.s3_client = boto3.client("s3")

    def create_dump(self) -> Path:
        """
        Create MySQL dump using mysqldump command.

        Returns:
            Path to the dump file
        """
        dump_filename = f"{self.db_name}.sql"
        dump_path = self.backup_dir / dump_filename

        print(f"Creating MySQL dump: {dump_filename}")

        # mysqldump command
        cmd = [
            "mysqldump",
            f"--host={self.db_host}",
            f"--user={self.db_user}",
            f"--password={self.db_password}",
            "--single-transaction",
            "--quick",
            "--lock-tables=false",
            "--ssl",
            "--ssl-verify-server-cert=0",
            self.db_name,
        ]

        try:
            with open(dump_path, "w") as f:
                subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    check=True,
                    text=True,
                )
            print(f"Dump created successfully: {dump_path}")
            return dump_path
        except subprocess.CalledProcessError as e:
            print(f"Error creating dump: {e.stderr}", file=sys.stderr)
            raise

    def compress_dump(self, dump_path: Path) -> Path:
        """
        Compress dump file using gzip.

        Args:
            dump_path: Path to the dump file

        Returns:
            Path to the compressed file
        """
        compressed_path = Path(f"{dump_path}.gz")
        print(f"Compressing dump file: {dump_path.name}")

        try:
            subprocess.run(
                ["gzip", "-f", str(dump_path)],
                check=True,
                stderr=subprocess.PIPE,
                text=True,
            )
            print(f"Compression completed: {compressed_path}")
            return compressed_path
        except subprocess.CalledProcessError as e:
            print(f"Error compressing file: {e.stderr}", file=sys.stderr)
            raise

    def upload_to_s3(self, file_path: Path) -> str:
        """
        Upload compressed dump to S3.

        Args:
            file_path: Path to the compressed dump file

        Returns:
            S3 URI of the uploaded file
        """
        s3_key = f"{self.s3_prefix}/{file_path.name}"
        print(f"Uploading to S3: s3://{self.s3_bucket}/{s3_key}")

        try:
            self.s3_client.upload_file(
                str(file_path),
                self.s3_bucket,
                s3_key,
                ExtraArgs={"StorageClass": "STANDARD_IA"},
            )
            s3_uri = f"s3://{self.s3_bucket}/{s3_key}"
            print(f"Upload completed: {s3_uri}")
            return s3_uri
        except ClientError as e:
            print(f"Error uploading to S3: {e}", file=sys.stderr)
            raise

    def cleanup(self, file_path: Path):
        """
        Clean up local backup file.

        Args:
            file_path: Path to the file to delete
        """
        if file_path.exists():
            print(f"Cleaning up local file: {file_path}")
            file_path.unlink()

    def run(self) -> str:
        """
        Execute the full backup process.

        Returns:
            S3 URI of the uploaded backup
        """
        print("=" * 60)
        print("MySQL Backup to S3 - Starting")
        print("=" * 60)

        dump_path = None
        compressed_path = None

        try:
            # Create dump
            dump_path = self.create_dump()

            # Compress dump
            compressed_path = self.compress_dump(dump_path)

            # Upload to S3
            s3_uri = self.upload_to_s3(compressed_path)

            print("=" * 60)
            print("Backup completed successfully!")
            print(f"S3 Location: {s3_uri}")
            print("=" * 60)

            return s3_uri

        except Exception as e:
            print("=" * 60)
            print(f"Backup failed: {e}", file=sys.stderr)
            print("=" * 60)
            raise

        finally:
            # Cleanup local files
            if compressed_path:
                self.cleanup(compressed_path)


def main():
    """
    Main function - Configure and run backup.
    """
    # Configuration from environment variables
    config = {
        "db_host": os.getenv("DB_HOST", "localhost"),
        "db_user": os.getenv("DB_USER", "root"),
        "db_password": os.getenv("DB_PASSWORD", ""),
        "db_name": os.getenv("DB_NAME", "mydb"),
        "s3_bucket": os.getenv("S3_BUCKET", "my-backup-bucket"),
        "s3_prefix": os.getenv("S3_PREFIX", "mysql-backups"),
        "backup_dir": os.getenv("BACKUP_DIR", "/tmp"),
    }

    # Validate required configuration
    if not config["db_password"]:
        print("Error: DB_PASSWORD environment variable is required", file=sys.stderr)
        sys.exit(1)

    if not config["s3_bucket"]:
        print("Error: S3_BUCKET environment variable is required", file=sys.stderr)
        sys.exit(1)

    # Run backup
    backup = MySQLBackupToS3(**config)
    backup.run()


if __name__ == "__main__":
    main()
