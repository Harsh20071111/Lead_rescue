import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

def safe_ident(identifier):
    """Quote an identifier to prevent SQL injection."""
    return f'"{identifier.replace(chr(34), chr(34)+chr(34))}"'

with connection.cursor() as cursor:
    cursor.execute(
        "SELECT relname, relkind FROM pg_class WHERE relname LIKE %s;",
        ['agencies_agency_slug%']
    )
    rows = cursor.fetchall()
    print("Found relations:", rows)
    for relname, relkind in rows:
        quoted = safe_ident(relname)
        if relkind == 'i':  # index
            cursor.execute(f"DROP INDEX IF EXISTS {quoted};")
            print(f"Dropped index {relname}")
        elif relkind == 'S':  # sequence
            cursor.execute(f"DROP SEQUENCE IF EXISTS {quoted};")
            print(f"Dropped sequence {relname}")
        else:
            print(f"Unknown relkind {relkind} for {relname}")
