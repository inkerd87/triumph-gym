from datetime import date, timedelta
from models.database import SessionLocal
from models.client import Client
from models.trainer import Trainer
from models.membership import Membership, ClientMembership
from models.visit import Visit

def populate():
    db = SessionLocal()

    # Очищаем старые данные
    print("Clearing old tables...")
    db.query(Visit).delete()
    db.query(ClientMembership).delete()
    db.query(Membership).delete()
    db.query(Client).delete()
    db.query(Trainer).delete()
    db.commit()

    print("Adding trainers...")
    trainers = [
        Trainer(full_name="Алексей Ковалев", phone="+7 999 111-22-33", specialization="Кроссфит / CrossFit"),
        Trainer(full_name="Мария Смирнова", phone="+7 999 222-33-44", specialization="Йога & Пилатес"),
        Trainer(full_name="Дмитрий Петров", phone="+7 999 333-44-55", specialization="Бодибилдинг"),
        Trainer(full_name="Елена Васильева", phone="+7 999 444-55-66", specialization="Стретчинг & Аэробика"),
        Trainer(full_name="Игорь Сидоров", phone="+7 999 555-66-77", specialization="Тяжелая атлетика")
    ]
    db.add_all(trainers)
    db.commit()

    print("Adding memberships...")
    memberships = [
        Membership(name="Триумф — разовый визит", duration_days=1, price=600.0),
        Membership(name="Триумф Стандарт", duration_days=30, price=3500.0),
        Membership(name="Триумф Студент", duration_days=30, price=2500.0),
        Membership(name="Триумф VIP", duration_days=90, price=14000.0),
        Membership(name="Триумф Год", duration_days=365, price=28000.0)
    ]
    db.add_all(memberships)
    db.commit()

    print("Adding clients...")
    clients = [
        Client(full_name="Иван Иванов", phone="+7 900 123-45-67", email="ivan@example.com", category="client"),
        Client(full_name="Екатерина Кузнецова", phone="+7 900 765-43-21", email="kate@example.com", category="vip"),
        Client(full_name="Александр Соколов", phone="+7 900 555-55-55", email="sokol@example.com", category="client"),
        Client(full_name="Сергей Морозов", phone="+7 900 111-22-33", email="morozov@example.com", category="client"),
        Client(full_name="Анна Павлова", phone="+7 900 222-33-44", email="annap@example.com", category="vip"),
        Client(full_name="Ольга Новикова", phone="+7 900 333-44-55", email="olga@example.com", category="client"),
        Client(full_name="Михаил Федоров", phone="+7 900 444-55-66", email="mikhail@example.com", category="trainer"),
        Client(full_name="Наталья Козлова", phone="+7 900 666-77-88", email="natalia@example.com", category="client"),
        Client(full_name="Артем Семенов", phone="+7 900 777-88-99", email="artem@example.com", category="client"),
        Client(full_name="Юлия Егорова", phone="+7 900 888-99-00", email="yulia@example.com", category="vip")
    ]
    db.add_all(clients)
    db.commit()

    print("Assigning memberships (active and expired)...")
    today = date.today()
    
    # Ссылки на объекты для удобства
    c_ivan, c_kate, c_sokol, c_serg, c_anna, c_olga, c_mikh, c_nat, c_art, c_yul = clients
    m_single, m_month, m_stud, m_vip, m_year = memberships
    t_alex, t_mary, t_dmit, t_elena, t_igor = trainers

    client_memberships = [
        # Активные
        ClientMembership(client_id=c_ivan.id, membership_id=m_month.id, start_date=today - timedelta(days=10), end_date=(today - timedelta(days=10)) + timedelta(days=m_month.duration_days)),
        ClientMembership(client_id=c_kate.id, membership_id=m_vip.id, start_date=today - timedelta(days=20), end_date=(today - timedelta(days=20)) + timedelta(days=m_vip.duration_days)),
        ClientMembership(client_id=c_serg.id, membership_id=m_stud.id, start_date=today - timedelta(days=5), end_date=(today - timedelta(days=5)) + timedelta(days=m_stud.duration_days)),
        ClientMembership(client_id=c_anna.id, membership_id=m_year.id, start_date=today - timedelta(days=100), end_date=(today - timedelta(days=100)) + timedelta(days=m_year.duration_days)),
        ClientMembership(client_id=c_mikh.id, membership_id=m_month.id, start_date=today - timedelta(days=2), end_date=(today - timedelta(days=2)) + timedelta(days=m_month.duration_days)),
        ClientMembership(client_id=c_yul.id, membership_id=m_vip.id, start_date=today - timedelta(days=1), end_date=(today - timedelta(days=1)) + timedelta(days=m_vip.duration_days)),
        
        # Просроченные (истекли 5 дней назад)
        ClientMembership(client_id=c_nat.id, membership_id=m_single.id, start_date=today - timedelta(days=6), end_date=today - timedelta(days=5)),
        ClientMembership(client_id=c_art.id, membership_id=m_month.id, start_date=today - timedelta(days=40), end_date=today - timedelta(days=10))
    ]
    db.add_all(client_memberships)
    db.commit()

    print("Registering historical visits...")
    visits = [
        # Сегодня
        Visit(client_id=c_ivan.id, trainer_id=t_alex.id, visit_date=today, note="Интенсивный функциональный тренинг"),
        Visit(client_id=c_kate.id, trainer_id=t_mary.id, visit_date=today, note="Индивидуальная растяжка"),
        Visit(client_id=c_serg.id, trainer_id=None, visit_date=today, note="Самостоятельная тренировка"),
        
        # Вчера
        Visit(client_id=c_anna.id, trainer_id=t_dmit.id, visit_date=today - timedelta(days=1), note="Работа на силу (приседания)"),
        Visit(client_id=c_yul.id, trainer_id=t_elena.id, visit_date=today - timedelta(days=1), note="Первый визит по VIP-тарифу"),
        Visit(client_id=c_mikh.id, trainer_id=t_igor.id, visit_date=today - timedelta(days=1), note="Подготовка к соревнованиям"),
        
        # 3 дня назад
        Visit(client_id=c_ivan.id, trainer_id=t_alex.id, visit_date=today - timedelta(days=3), note="Кардио сессия"),
        Visit(client_id=c_kate.id, trainer_id=t_mary.id, visit_date=today - timedelta(days=3), note="Медитация и дыхание"),
        Visit(client_id=c_olga.id, trainer_id=None, visit_date=today - timedelta(days=3), note="Пробное занятие"),
        
        # 5 дней назад (когда у Натальи был активный разовый абонемент)
        Visit(client_id=c_nat.id, trainer_id=t_elena.id, visit_date=today - timedelta(days=5), note="Разовая тренировка по абонементу"),
        
        # 6 дней назад
        Visit(client_id=c_art.id, trainer_id=t_dmit.id, visit_date=today - timedelta(days=6), note="Проработка спины")
    ]
    db.add_all(visits)
    db.commit()

    print("Large mock dataset populated successfully!")
    db.close()

if __name__ == '__main__':
    populate()
