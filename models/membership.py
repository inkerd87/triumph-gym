from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date
from sqlalchemy.orm import relationship
from .database import Base

class Membership(Base):
    __tablename__ = 'memberships'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    duration_days = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)

class ClientMembership(Base):
    __tablename__ = 'client_memberships'
    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey('clients.id'), nullable=False)
    membership_id = Column(Integer, ForeignKey('memberships.id'), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    client = relationship('Client', back_populates='memberships')
    membership = relationship('Membership')
