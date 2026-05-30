from models.database import engine
from sqlalchemy import text

def add_columns():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE class_sessions ADD COLUMN client_id INTEGER REFERENCES clients(id);"))
            print("Added client_id column.")
        except Exception as e:
            print("Failed to add client_id:", e)
            
        try:
            conn.execute(text("ALTER TABLE class_sessions ADD COLUMN note VARCHAR;"))
            print("Added note column.")
        except Exception as e:
            print("Failed to add note:", e)
            
        conn.commit()

if __name__ == "__main__":
    add_columns()
