from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from .person import Person

class Trainer(Person):
    __tablename__ = 'trainers'
    specialization = Column(String, nullable=False)

    # Relationships
    visits = relationship('Visit', back_populates='trainer')

    def get_role_description(self):
        return f"Тренер: спец. {self.specialization}"
