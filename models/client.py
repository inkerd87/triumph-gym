import re

from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash

from .person import Person


class Client(Person):
    __tablename__ = 'clients'
    email = Column(String, nullable=True)
    category = Column(String, nullable=False, default='client')
    created_at = Column(DateTime, default=datetime.utcnow)
    _pin_hash = Column('pin_hash', String, nullable=True)

    # Relationships
    visits = relationship('Visit', back_populates='client', cascade="all, delete-orphan")
    memberships = relationship('ClientMembership', back_populates='client', cascade="all, delete-orphan")

    def get_role_description(self):
        if self.category.lower() == 'vip':
            return "Клиент категории VIP"
        return f"Клиент категории {self.category}"

    def set_pin(self, raw_pin: str):
        self._pin_hash = generate_password_hash(str(raw_pin).strip(), method='pbkdf2:sha256')

    def check_pin(self, raw_pin: str) -> bool:
        pin = str(raw_pin).strip()
        if not pin:
            return False
        if self._pin_hash:
            return check_password_hash(self._pin_hash, pin)
        digits = re.sub(r'\D', '', self.phone or '')
        if len(digits) >= 4:
            return pin == digits[-4:]
        return pin == digits

    @property
    def uses_default_pin(self) -> bool:
        return not self._pin_hash
