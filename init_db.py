from models.database import engine, Base, SessionLocal
from models.admin import Admin
import models

def init_db():
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    admin = db.query(Admin).filter_by(username='admin').first()
    if not admin:
        admin = Admin(username='admin')
        admin.set_password('admin123')
        db.add(admin)
        db.commit()
        print("Default admin user created.")
    else:
        print("Admin user already exists.")
    
    db.close()
    print("Database initialized.")

if __name__ == '__main__':
    init_db()
