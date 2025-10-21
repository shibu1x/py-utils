#!/usr/bin/env python3
"""
Script to import CSV files into MySQL credit_histories table
"""
import csv
import os
import unicodedata
from datetime import datetime
from typing import Optional
from pathlib import Path
import mysql.connector
from mysql.connector import Error


def connect_to_mysql(
    host: str = "localhost",
    database: str = "your_database",
    user: str = "your_user",
    password: str = "your_password"
) -> Optional[mysql.connector.MySQLConnection]:
    """Connect to MySQL database"""
    try:
        connection = mysql.connector.connect(
            host=host,
            database=database,
            user=user,
            password=password,
            charset='utf8mb4'
        )
        if connection.is_connected():
            print(f"Connected to MySQL database: {database}")
            return connection
    except Error as e:
        print(f"Error: {e}")
        return None


def parse_csv_row(row: list, card_number: str, service: str) -> Optional[dict]:
    """Parse CSV row and return data dictionary"""
    # Skip header rows and card number rows
    if not row or len(row) < 6:
        return None

    # Skip rows with empty date (e.g., total rows)
    if not row[0] or not row[0].strip():
        return None

    # Check date format
    try:
        used_at = datetime.strptime(row[0].strip(), '%Y/%m/%d').date()
    except ValueError:
        return None

    store = row[1].strip() if len(row) > 1 else ""
    # Normalize store name (NFKC: convert full-width alphanumeric/symbols to half-width)
    store = unicodedata.normalize('NFKC', store)

    # Parse price (remove commas)
    try:
        price = int(row[2].replace(',', '').strip()) if len(row) > 2 and row[2].strip() else 0
    except ValueError:
        price = 0

    # Calculate payment from installment info
    # row[3]: payment count, row[4]: installment count, row[5]: payment amount
    try:
        payment = int(row[5].replace(',', '').strip()) if len(row) > 5 and row[5].strip() else price
    except ValueError:
        payment = price

    # Note (if row[6] exists)
    note = row[6].strip() if len(row) > 6 and row[6].strip() else None
    # Normalize note (NFKC: convert full-width alphanumeric/symbols to half-width)
    if note:
        note = unicodedata.normalize('NFKC', note)

    return {
        'used_at': used_at,
        'store': store,
        'price': price,
        'payment': payment,
        'note': note,
        'service': service,
        'card_number': card_number
    }


def import_csv_to_mysql(
    csv_file: str,
    connection: mysql.connector.MySQLConnection,
    service: str = "vpass"
) -> int:
    """Import CSV file to MySQL"""
    cursor = connection.cursor()

    # Get file name
    file_name = os.path.basename(csv_file)

    # Check if data with same service and file already exists
    check_query = """
    SELECT COUNT(*) FROM credit_histories
    WHERE service = %s AND file = %s
    """
    cursor.execute(check_query, (service, file_name))
    count = cursor.fetchone()[0]

    if count > 0:
        print(f"Skipped: Data with service='{service}' and file='{file_name}' already exists")
        cursor.close()
        return 0

    insert_query = """
    INSERT INTO credit_histories
    (used_at, store, price, payment, note, service, file, created_at, updated_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    inserted_count = 0
    current_card_number = ""

    try:
        # Read CSV file (Shift-JIS encoding)
        with open(csv_file, 'r', encoding='shift_jis') as file:
            csv_reader = csv.reader(file)

            for row in csv_reader:
                # Detect card number row
                if len(row) > 1 and row[1] and '-' in row[1] and '*' in row[1]:
                    current_card_number = row[1].strip()
                    continue

                # Parse data row
                data = parse_csv_row(row, current_card_number, service)
                if data is None:
                    continue

                # Get timestamp
                now = datetime.now()

                # Insert data
                values = (
                    data['used_at'],
                    data['store'],
                    data['price'],
                    data['payment'],
                    data['note'],
                    data['service'],
                    file_name,
                    now,
                    now
                )

                cursor.execute(insert_query, values)
                inserted_count += 1
                print(f"Inserted: {data['used_at']} - {data['store']} - ¥{data['price']:,}")

        # Commit
        connection.commit()
        print(f"\nTotal {inserted_count} records inserted")
        return inserted_count

    except Error as e:
        print(f"Error: {e}")
        connection.rollback()
        return 0
    finally:
        cursor.close()


def main():
    """Main processing"""
    # Database connection settings (from environment variables or defaults)
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'database': os.getenv('DB_NAME', 'your_database'),
        'user': os.getenv('DB_USER', 'your_user'),
        'password': os.getenv('DB_PASSWORD', 'your_password')
    }

    # CSV files directory (relative path from main.py)
    script_dir = Path(__file__).parent
    csv_directory = script_dir / 'csv_data'

    # Service type ('vpass' or 'enavi')
    service = 'vpass'

    # Connect to MySQL
    connection = connect_to_mysql(**db_config)
    if connection is None:
        print("Failed to connect to database")
        return

    try:
        # Get all CSV files in directory
        csv_files = sorted(csv_directory.glob('*.csv'))

        if not csv_files:
            print(f"No CSV files found in: {csv_directory}")
            return

        print(f"Found {len(csv_files)} CSV file(s)\n")

        # Import each CSV file
        total_inserted = 0
        for csv_file in csv_files:
            print(f"{'='*60}")
            print(f"Processing: {csv_file.name}")
            print(f"{'='*60}")
            inserted = import_csv_to_mysql(str(csv_file), connection, service)
            total_inserted += inserted
            print()

        print(f"{'='*60}")
        print(f"All processing completed: Total {total_inserted} records inserted")
        print(f"{'='*60}")

    finally:
        if connection.is_connected():
            connection.close()
            print("\nMySQL connection closed")


if __name__ == "__main__":
    main()
