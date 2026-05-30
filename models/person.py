from sqlalchemy import Column, Integer, String
from .database import Base

class Person(Base):
    __abstract__ = True
    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String, nullable=False)
    phone = Column(String, nullable=False, unique=True)

    def get_role_description(self):
        return "Базовый пользователь"
