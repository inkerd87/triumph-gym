from sqlalchemy import inspect, text

from models.database import engine


def migrate_client_pin_column():
    insp = inspect(engine)
    if 'clients' not in insp.get_table_names():
        return
    cols = {c['name'] for c in insp.get_columns('clients')}
    if 'pin_hash' in cols:
        return
    with engine.begin() as conn:
        conn.execute(text('ALTER TABLE clients ADD COLUMN pin_hash VARCHAR'))


def migrate_visit_presence_columns():
    insp = inspect(engine)
    if 'attendance' not in insp.get_table_names():
        return
    cols = {c['name'] for c in insp.get_columns('attendance')}
    with engine.begin() as conn:
        if 'check_in_at' not in cols:
            conn.execute(text('ALTER TABLE attendance ADD COLUMN check_in_at TIMESTAMP'))
        if 'check_out_at' not in cols:
            conn.execute(text('ALTER TABLE attendance ADD COLUMN check_out_at TIMESTAMP'))

    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE attendance
            SET check_in_at = visit_date::timestamp + time '10:00'
            WHERE check_in_at IS NULL
        """))
        conn.execute(text("""
            UPDATE attendance
            SET check_out_at = check_in_at + interval '2 hours'
            WHERE check_out_at IS NULL AND check_in_at IS NOT NULL
        """))


def run_migrations():
    migrate_client_pin_column()
    migrate_visit_presence_columns()
