from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from .database import Base

class Admin(Base):
    __tablename__ = 'admins'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False, unique=True)
    _password_hash = Column('password_hash', String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def set_password(self, raw_password):
        self._password_hash = generate_password_hash(raw_password, method='pbkdf2:sha256')

    def check_password(self, raw_password):
        return check_password_hash(self._password_hash, raw_password)
