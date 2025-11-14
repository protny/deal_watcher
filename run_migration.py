"""Run database migration to rename metadata to extra_data."""

import os
import sys
from dotenv import load_dotenv
import psycopg2

# Load environment variables
load_dotenv()

def run_migration():
    """Run the migration."""
    conn_string = os.getenv('DB_CONNECTION_STRING')

    if not conn_string:
        print("ERROR: DB_CONNECTION_STRING not set in .env file")
        print("\nPlease create a .env file with:")
        print("DB_CONNECTION_STRING=postgresql://user:password@host:port/database")
        sys.exit(1)

    print(f"Connecting to database...")

    try:
        # Connect to database
        conn = psycopg2.connect(conn_string)
        conn.autocommit = True
        cursor = conn.cursor()

        print("Running migration...")

        # Check if column exists
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='deals' AND column_name='metadata'
        """)

        if cursor.fetchone():
            print("  - Renaming metadata column to extra_data...")
            cursor.execute("ALTER TABLE deals RENAME COLUMN metadata TO extra_data")
            print("    ✓ Column renamed")
        else:
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='deals' AND column_name='extra_data'
            """)
            if cursor.fetchone():
                print("  - Column already named extra_data, skipping")
            else:
                print("  - WARNING: Neither metadata nor extra_data column found!")

        # Update index
        print("  - Updating index...")
        cursor.execute("DROP INDEX IF EXISTS idx_deals_metadata")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_deals_extra_data ON deals USING gin(extra_data)")
        print("    ✓ Index updated")

        cursor.close()
        conn.close()

        print("\n✓ Migration completed successfully!")

    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    run_migration()
