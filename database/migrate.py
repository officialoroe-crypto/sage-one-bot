from sqlalchemy import inspect, text
from database.connection import engine
from database import models  # noqa: F401


def migrate():
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if "execution_events" not in tables:
        models.ExecutionEvent.__table__.create(bind=engine, checkfirst=True)
        tables = inspect(engine).get_table_names()
        print("ADDED: execution_events")

    if "automations" not in tables:
        models.Automation.__table__.create(bind=engine, checkfirst=True)
        tables = inspect(engine).get_table_names()
        print("ADDED: automations")

    if "sales_leads" not in tables:
        from sales.models import SalesLead
        SalesLead.__table__.create(bind=engine, checkfirst=True)
        tables = inspect(engine).get_table_names()
        print("ADDED: sales_leads")

    if "sales_activities" not in tables:
        from sales.models import SalesActivity
        SalesActivity.__table__.create(bind=engine, checkfirst=True)
        tables = inspect(engine).get_table_names()
        print("ADDED: sales_activities")

    if "developer_proposals" not in tables:
        models.DeveloperProposal.__table__.create(bind=engine, checkfirst=True)
        tables = inspect(engine).get_table_names()
        print("ADDED: developer_proposals")

    if "sessions" in tables:
        session_columns = {column["name"] for column in inspector.get_columns("sessions")}
        with engine.begin() as connection:
            if "profile_id" not in session_columns:
                connection.execute(text("ALTER TABLE sessions ADD COLUMN profile_id VARCHAR"))
                print("ADDED: sessions.profile_id")
            if "owner_key" not in session_columns:
                connection.execute(text("ALTER TABLE sessions ADD COLUMN owner_key VARCHAR"))
                print("ADDED: sessions.owner_key")

    if "memories" in tables:
        memory_columns = {column["name"] for column in inspector.get_columns("memories")}
        with engine.begin() as connection:
            if "owner_key" not in memory_columns:
                connection.execute(text("ALTER TABLE memories ADD COLUMN owner_key VARCHAR"))
                print("ADDED: memories.owner_key")
            if "profile_id" not in memory_columns:
                connection.execute(text("ALTER TABLE memories ADD COLUMN profile_id VARCHAR"))
                print("ADDED: memories.profile_id")

    for table_name, column_name in [("missions", "owner_key"), ("notifications", "owner_key"), ("action_logs", "owner_key"), ("research_records", "owner_key")]:
        if table_name in tables:
            columns = {column["name"] for column in inspector.get_columns(table_name)}
            if column_name not in columns:
                with engine.begin() as connection:
                    connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} VARCHAR"))
                print(f"ADDED: {table_name}.{column_name}")

    if "tasks" not in tables:
        print("TASK TABLE DOES NOT EXIST.")
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("tasks")
    }

    migrations = [
        ("owner_key", "ALTER TABLE tasks ADD COLUMN owner_key VARCHAR"),
        ("premium_work_key", "ALTER TABLE tasks ADD COLUMN premium_work_key VARCHAR"),
        ("profile_id", "ALTER TABLE tasks ADD COLUMN profile_id VARCHAR"),
        ("project_id", "ALTER TABLE tasks ADD COLUMN project_id VARCHAR"),
        ("mission_id", "ALTER TABLE tasks ADD COLUMN mission_id VARCHAR"),
        ("depends_on", "ALTER TABLE tasks ADD COLUMN depends_on TEXT"),
        ("verification_status", "ALTER TABLE tasks ADD COLUMN verification_status VARCHAR DEFAULT 'pending'"),
        ("worker_id", "ALTER TABLE tasks ADD COLUMN worker_id VARCHAR"),
        ("lease_expires_at", "ALTER TABLE tasks ADD COLUMN lease_expires_at DATETIME"),
        ("heartbeat_at", "ALTER TABLE tasks ADD COLUMN heartbeat_at DATETIME"),
        ("next_retry_at", "ALTER TABLE tasks ADD COLUMN next_retry_at DATETIME"),
    ]

    if "action_logs" in tables:
        action_columns = {
            column["name"]
            for column in inspector.get_columns("action_logs")
        }
        action_migrations = [
            ("mission_id", "ALTER TABLE action_logs ADD COLUMN mission_id VARCHAR"),
            ("parent_action_id", "ALTER TABLE action_logs ADD COLUMN parent_action_id VARCHAR"),
            ("source", "ALTER TABLE action_logs ADD COLUMN source VARCHAR DEFAULT 'sage'"),
        ]
    else:
        action_migrations = []

    applied = 0

    with engine.begin() as connection:
        for column_name, sql in migrations:
            if column_name in existing_columns:
                print(f"SKIP: {column_name}")
                continue

            connection.execute(text(sql))
            print(f"ADDED: {column_name}")
            applied += 1

        for column_name, sql in action_migrations:
            if column_name in action_columns:
                print(f"SKIP: action_logs.{column_name}")
                continue

            connection.execute(text(sql))
            print(f"ADDED: action_logs.{column_name}")
            applied += 1

    print(f"SAGE DATABASE MIGRATION COMPLETE. {applied} change(s) applied.")


if __name__ == "__main__":
    migrate()
