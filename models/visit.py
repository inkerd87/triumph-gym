from sqlalchemy import Column, Integer, String, ForeignKey, Date, DateTime
from sqlalchemy.orm import relationship
from .database import Base


class Visit(Base):
    __tablename__ = 'attendance'
    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey('clients.id'), nullable=False)
    trainer_id = Column(Integer, ForeignKey('trainers.id'), nullable=True)
    visit_date = Column(Date, nullable=False)
    check_in_at = Column(DateTime, nullable=True)
    check_out_at = Column(DateTime, nullable=True)
    note = Column(String, nullable=True)

    @property
    def is_in_gym(self) -> bool:
        return self.check_out_at is None

    client = relationship('Client', back_populates='visits')
    trainer = relationship('Trainer', back_populates='visits')
