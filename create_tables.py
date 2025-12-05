from app import db, app
from sqlalchemy import text

with app.app_context():
    db.create_all()
    print("All tables created successfully!")

    table_name = 'detection_department'
    column_name = 'department'

    check_query = text(f"""
        SELECT column_name 
        FROM information_schema.columns
        WHERE table_name=:table AND column_name=:column;
    """)

    with db.engine.begin() as conn:
        result = conn.execute(check_query, {"table": table_name, "column": column_name})

        if result.fetchone():
            print(f"Column '{column_name}' already exists.")
        else:
            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} VARCHAR;"))
            print(f"Column '{column_name}' added.")

            conn.execute(text(f"UPDATE {table_name} SET {column_name}='Ward Office' WHERE {column_name} IS NULL;"))
            print("Existing rows updated.")

            conn.execute(text(f"ALTER TABLE {table_name} ALTER COLUMN {column_name} SET NOT NULL;"))
            print("Column set to NOT NULL.")
