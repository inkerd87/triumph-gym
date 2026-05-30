from datetime import datetime

from models.visit import Visit
from services.attendance_service import AttendanceService


def count_in_gym(db) -> int:
    return db.query(Visit).filter(Visit.check_out_at.is_(None)).count()


def get_open_visit(db, client_id: int):
    return (
        db.query(Visit)
        .filter(Visit.client_id == client_id, Visit.check_out_at.is_(None))
        .order_by(Visit.check_in_at.desc())
        .first()
    )


def list_in_gym(db, limit=50):
    return (
        db.query(Visit)
        .filter(Visit.check_out_at.is_(None))
        .order_by(Visit.check_in_at.desc())
        .limit(limit)
        .all()
    )


def check_in(db, client, trainer=None, strict=True) -> Visit:
    if get_open_visit(db, client.id):
        raise Exception("Уже отмечен в зале")

    now = datetime.now()
    service = AttendanceService(db)
    visit = service.register_visit(client, now.date(), trainer, strict=strict)
    visit.check_in_at = now
    visit.check_out_at = None
    db.commit()
    db.refresh(visit)
    return visit


def check_out(db, client) -> Visit:
    visit = get_open_visit(db, client.id)
    if not visit:
        raise Exception("Не в зале — выход не отмечен")
    visit.check_out_at = datetime.now()
    db.commit()
    db.refresh(visit)
    return visit
