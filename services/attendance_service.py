from datetime import datetime

from models.visit import Visit
from services.membership_service import MembershipService


class AttendanceService:
    def __init__(self, db_session):
        self.db = db_session
        self.membership_service = MembershipService(db_session)

    def register_visit(self, client, current_date, trainer=None, strict=True):
        if strict and not self.membership_service.check_active_status(client, current_date):
            raise Exception("Абонемент истек")

        now = datetime.now()
        visit = Visit(
            client_id=client.id,
            trainer_id=trainer.id if trainer else None,
            visit_date=current_date,
            check_in_at=now,
            check_out_at=None,
        )
        self.db.add(visit)
        self.db.commit()
        self.db.refresh(visit)
        return visit
