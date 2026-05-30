from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class ClassSession(Base):
    __tablename__ = 'class_sessions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    trainer_id = Column(Integer, ForeignKey('trainers.id'), nullable=True)
    client_id = Column(Integer, ForeignKey('clients.id'), nullable=True)
    start_time = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=60, nullable=False)
    note = Column(String, nullable=True)

    trainer = relationship('Trainer')
    client = relationship('Client')
