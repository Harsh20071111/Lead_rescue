import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SELECT relname, relkind FROM pg_class WHERE relname LIKE 'agencies_agency_slug%';")
    rows = cursor.fetchall()
    print("Found relations:", rows)
    for relname, relkind in rows:
        if relkind == 'i': # index
            cursor.execute(f"DROP INDEX IF EXISTS {relname};")
            print(f"Dropped index {relname}")
        elif relkind == 'S': # sequence
            cursor.execute(f"DROP SEQUENCE IF EXISTS {relname};")
            print(f"Dropped sequence {relname}")
        else:
            print(f"Unknown relkind {relkind} for {relname}")
