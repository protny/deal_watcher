#!/usr/bin/env python3
"""Validation script to check if deal_watcher is properly configured."""

import os
import sys
from pathlib import Path

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def print_success(msg):
    print(f"{GREEN}✓{RESET} {msg}")

def print_error(msg):
    print(f"{RED}✗{RESET} {msg}")

def print_warning(msg):
    print(f"{YELLOW}⚠{RESET} {msg}")

def check_python_version():
    """Check Python version."""
    if sys.version_info >= (3, 10):
        print_success(f"Python version: {sys.version.split()[0]}")
        return True
    else:
        print_error(f"Python version too old: {sys.version.split()[0]} (need 3.10+)")
        return False

def check_dependencies():
    """Check if required dependencies are installed."""
    required = [
        ('requests', 'HTTP requests'),
        ('bs4', 'BeautifulSoup4 (HTML parsing)'),
        ('lxml', 'LXML (parser)'),
        ('sqlalchemy', 'SQLAlchemy (ORM)'),
        ('psycopg2', 'PostgreSQL driver'),
        ('dotenv', 'python-dotenv'),
    ]

    all_ok = True
    for module, desc in required:
        try:
            __import__(module)
            print_success(f"{desc}")
        except ImportError:
            print_error(f"{desc} - NOT INSTALLED")
            all_ok = False

    return all_ok

def check_config_file():
    """Check if config file exists."""
    config_path = Path('deal_watcher/config/config.json')
    if config_path.exists():
        print_success(f"Config file exists: {config_path}")
        return True
    else:
        print_error(f"Config file missing: {config_path}")
        return False

def check_env_file():
    """Check if .env file exists and has DB_CONNECTION_STRING."""
    env_path = Path('.env')
    if not env_path.exists():
        print_warning(".env file not found")
        print("  Create .env with: DB_CONNECTION_STRING=postgresql://...")
        return False

    with open(env_path) as f:
        content = f.read()

    if 'DB_CONNECTION_STRING' in content:
        print_success(".env file exists with DB_CONNECTION_STRING")
        return True
    else:
        print_error(".env file exists but missing DB_CONNECTION_STRING")
        return False

def check_database_connection():
    """Check if database is accessible."""
    try:
        from dotenv import load_dotenv
        import psycopg2

        load_dotenv()
        conn_string = os.getenv('DB_CONNECTION_STRING')

        if not conn_string:
            print_error("DB_CONNECTION_STRING not set")
            return False

        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()

        print_success("Database connection successful")
        return True

    except Exception as e:
        print_error(f"Database connection failed: {e}")
        return False

def check_database_schema():
    """Check if database has correct schema."""
    try:
        from dotenv import load_dotenv
        import psycopg2

        load_dotenv()
        conn_string = os.getenv('DB_CONNECTION_STRING')

        if not conn_string:
            return False

        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor()

        # Check if deals table has extra_data column
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='deals' AND column_name='extra_data'
        """)

        if cursor.fetchone():
            print_success("Database schema is up to date (extra_data column exists)")
            schema_ok = True
        else:
            # Check if it has old metadata column
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='deals' AND column_name='metadata'
            """)

            if cursor.fetchone():
                print_error("Database schema needs migration (metadata → extra_data)")
                print("  Run: python3 run_migration.py")
                schema_ok = False
            else:
                print_error("Database schema incomplete (no deals table?)")
                print("  Run: psql -d deal_watcher -f database/schema.sql")
                schema_ok = False

        # Check if categories exist
        cursor.execute("SELECT COUNT(*) FROM categories")
        count = cursor.fetchone()[0]
        if count > 0:
            print_success(f"Categories table populated ({count} categories)")
        else:
            print_warning("Categories table is empty")
            print("  Run: psql -d deal_watcher -f database/schema.sql")

        cursor.close()
        conn.close()

        return schema_ok

    except Exception as e:
        print_error(f"Database schema check failed: {e}")
        return False

def check_project_structure():
    """Check if project structure is correct."""
    required_dirs = [
        'deal_watcher',
        'deal_watcher/config',
        'deal_watcher/scrapers',
        'deal_watcher/filters',
        'deal_watcher/database',
        'deal_watcher/utils',
    ]

    all_ok = True
    for dir_path in required_dirs:
        if Path(dir_path).is_dir():
            print_success(f"Directory exists: {dir_path}")
        else:
            print_error(f"Directory missing: {dir_path}")
            all_ok = False

    return all_ok

def test_import_modules():
    """Test if main modules can be imported."""
    modules = [
        'deal_watcher.utils.logger',
        'deal_watcher.utils.http_client',
        'deal_watcher.scrapers.bazos_scraper',
        'deal_watcher.filters.auto_filter',
        'deal_watcher.filters.reality_filter',
        'deal_watcher.database.repository',
    ]

    all_ok = True
    for module in modules:
        try:
            __import__(module)
            print_success(f"Module imports OK: {module}")
        except Exception as e:
            print_error(f"Module import failed: {module}")
            print(f"  Error: {e}")
            all_ok = False

    return all_ok

def main():
    """Run all validation checks."""
    print("=" * 60)
    print("Deal Watcher - Setup Validation")
    print("=" * 60)

    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Project Structure", check_project_structure),
        ("Config File", check_config_file),
        ("Environment File", check_env_file),
        ("Database Connection", check_database_connection),
        ("Database Schema", check_database_schema),
        ("Module Imports", test_import_modules),
    ]

    results = []

    for name, check_func in checks:
        print(f"\n--- {name} ---")
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print_error(f"Check failed with exception: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"{status} - {name}")

    print(f"\n{passed}/{total} checks passed")

    if passed == total:
        print(f"\n{GREEN}✓ All checks passed! You're ready to run the scraper.{RESET}")
        print("\nNext steps:")
        print("  1. python -m deal_watcher.main  # Run the scraper")
        print("  2. Check database for results")
        return 0
    else:
        print(f"\n{RED}✗ Some checks failed. Please fix the issues above.{RESET}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
