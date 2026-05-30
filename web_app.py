import os
import math
import csv
import io
import re
from datetime import datetime, timedelta
from functools import wraps

from helpers import format_phone
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for, Response, make_response, g
from sqlalchemy import func, distinct
from flask.views import MethodView

from models.database import get_db, Base, engine, SessionLocal
import models  # noqa: F401 — регистрация моделей для create_all
from models.admin import Admin
from models.client import Client
from models.trainer import Trainer
from models.membership import Membership, ClientMembership
from models.visit import Visit
from models.session import ClassSession
from sqlalchemy.orm import joinedload
from repositories.client_repository import ClientRepository
from services.membership_service import MembershipService
from services.attendance_service import AttendanceService
from services.gym_presence import check_in, check_out, count_in_gym, get_open_visit
from db_migrations import run_migrations

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "triumph-gym-secret-key")


def ensure_database():
    Base.metadata.create_all(bind=engine)
    run_migrations()
    db = SessionLocal()
    try:
        admin = db.query(Admin).filter_by(username="admin").first()
        if not admin:
            admin = Admin(username="admin")
            admin.set_password("admin123")
            db.add(admin)
            db.commit()
    finally:
        db.close()


ensure_database()

@app.before_request
def before_request():
    g.db = SessionLocal()

@app.teardown_appcontext
def teardown_db(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()

CLIENT_CATEGORIES = ("client", "vip", "trainer")


def is_ajax_request():
    return request.headers.get("X-Requested-With") == "fetch"


def render_dashboard(db, **extra):
    data = get_dashboard_data(db)
    ctx = {
        "report_rows": None,
        "report_period": None,
        "category_label": category_label,
        **data,
        **extra,
    }
    return render_template("dashboard.html", **ctx)


def visit_counts(db, day):
    visits_today = db.query(Visit).filter(Visit.visit_date == day).count()
    unique_today = (
        db.query(func.count(distinct(Visit.client_id)))
        .filter(Visit.visit_date == day)
        .scalar()
        or 0
    )
    return visits_today, unique_today

def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapped

class LoginView(MethodView):
    def get(self):
        if session.get("admin_id"):
            return redirect(url_for("index"))
        return render_template("login.html")

    def post(self):
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if not username or not password:
            flash("Введите логин и пароль.")
            return redirect(url_for("login"))
        
        db = g.db
        admin = db.query(Admin).filter(Admin.username == username).first()
        if not admin or not admin.check_password(password):
            flash("Неверный логин или пароль.")
            return redirect(url_for("login"))
        
        session["admin_id"] = admin.id
        session["admin_username"] = admin.username
        flash("Вход выполнен.")
        return redirect(url_for("index"))

class LogoutView(MethodView):
    def post(self):
        session.clear()
        flash("Вы вышли из админки.")
        return redirect(url_for("login"))

def get_dashboard_data(db):
    clients = db.query(Client).order_by(Client.id.desc()).all()
    trainers = db.query(Trainer).order_by(Trainer.id.desc()).all()
    memberships = db.query(Membership).order_by(Membership.id.desc()).all()
    
    stats = {
        "clients_count": db.query(Client).count(),
        "vip_clients_count": db.query(Client).filter(Client.category == 'vip').count(),
        "regular_clients_count": db.query(Client).filter(Client.category == 'client').count(),
        "trainer_clients_count": db.query(Client).filter(Client.category == 'trainer').count(),
        "trainers_count": db.query(Trainer).count(),
        "memberships_count": db.query(Membership).count(),
        "visits_count": db.query(Visit).count(),
        "active_memberships_count": db.query(ClientMembership).filter(ClientMembership.end_date >= datetime.now().date()).count(),
    }
    
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    visits_today, unique_visitors_today = visit_counts(db, today)
    visits_yesterday = db.query(Visit).filter(Visit.visit_date == yesterday).count()
    if visits_yesterday:
        visits_trend_pct = round((visits_today - visits_yesterday) / visits_yesterday * 100)
    else:
        visits_trend_pct = 100 if visits_today else 0

    recent_visits = (
        db.query(Visit)
        .options(joinedload(Visit.client), joinedload(Visit.trainer))
        .order_by(Visit.id.desc())
        .limit(8)
        .all()
    )

    day_start = datetime.combine(today, datetime.min.time())
    day_end = datetime.combine(today, datetime.max.time())
    sessions_today = (
        db.query(ClassSession)
        .filter(ClassSession.start_time >= day_start, ClassSession.start_time <= day_end)
        .count()
    )

    hour = datetime.now().hour
    if hour < 12:
        greeting = "Доброе утро"
    elif hour < 18:
        greeting = "Добрый день"
    else:
        greeting = "Добрый вечер"

    chart_labels = []
    chart_data = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        chart_labels.append(d.strftime("%d.%m"))
        chart_data.append(db.query(Visit).filter(Visit.visit_date == d).count())

    week_ago = today - timedelta(days=6)
    top_rows = (
        db.query(Visit.client_id, func.count(Visit.id).label("cnt"))
        .filter(Visit.visit_date >= week_ago, Visit.visit_date <= today)
        .group_by(Visit.client_id)
        .order_by(func.count(Visit.id).desc())
        .limit(3)
        .all()
    )
    top_visitors = []
    for client_id, cnt in top_rows:
        c = db.query(Client).get(client_id)
        if c:
            top_visitors.append({"name": c.full_name, "count": cnt})

    expiring_soon = (
        db.query(ClientMembership)
        .options(joinedload(ClientMembership.client), joinedload(ClientMembership.membership))
        .filter(
            ClientMembership.end_date >= today,
            ClientMembership.end_date <= today + timedelta(days=7),
        )
        .order_by(ClientMembership.end_date)
        .limit(5)
        .all()
    )

    return {
        "clients": clients,
        "trainers": trainers,
        "memberships": memberships,
        "stats": stats,
        "categories": CLIENT_CATEGORIES,
        "chart_labels": chart_labels,
        "chart_data": chart_data,
        "greeting": greeting,
        "today_str": today.strftime("%d.%m.%Y"),
        "today_iso": today.isoformat(),
        "visits_today": visits_today,
        "unique_visitors_today": unique_visitors_today,
        "visits_trend_pct": visits_trend_pct,
        "recent_visits": recent_visits,
        "sessions_today": sessions_today,
        "top_visitors": top_visitors,
        "expiring_soon": expiring_soon,
        "in_gym_count": count_in_gym(db),
        "allow_demo_seed": os.getenv("ALLOW_DEMO_SEED") == "1",
    }

def category_label(value):
    labels = {"client": "Клиент", "vip": "VIP клиент", "trainer": "Тренер"}
    return labels.get(value, "Клиент")

class DemoSeedView(MethodView):
    """Одноразовая заливка демо-данных без Render Shell (нужен ALLOW_DEMO_SEED=1)."""
    decorators = [login_required]

    def post(self):
        if os.getenv("ALLOW_DEMO_SEED") != "1":
            flash("Демо-заливка отключена.")
            return redirect(url_for("index"))
        try:
            from populate_db import populate
            from populate_schedule import populate_schedule

            populate()
            populate_schedule()
            flash("Демо-данные загружены: клиенты, тренеры, тарифы, визиты и расписание.")
        except Exception as e:
            flash(f"Ошибка заливки: {e}")
        return redirect(url_for("index"))


class IndexView(MethodView):
    decorators = [login_required]

    def get(self):
        db = g.db
        data = get_dashboard_data(db)
        return render_template("dashboard.html", report_rows=None, report_period=None, category_label=category_label, **data)

class ClientListView(MethodView):
    decorators = [login_required]

    def get(self):
        db = g.db
        search_query = request.args.get("q", "").strip()
        category = request.args.get("category", "all").strip()
        membership_status = request.args.get("membership_status", "all").strip()
        page = request.args.get("page", 1, type=int)
        per_page = 20
        
        query = db.query(Client).order_by(Client.id.desc())
        
        if search_query:
            q = search_query.lower()
            clean_q = "".join(filter(str.isdigit, q))
            clients_all = query.all()
            filtered_clients = []
            for c in clients_all:
                norm_phone = "".join(filter(str.isdigit, c.phone or ""))
                name_match = q in (c.full_name or "").lower()
                email_match = q in (c.email or "").lower()
                phone_match = q in (c.phone or "").lower()
                clean_phone_match = bool(clean_q and (clean_q in norm_phone))
                
                if name_match or email_match or phone_match or clean_phone_match:
                    filtered_clients.append(c)
            all_matching = filtered_clients
        else:
            all_matching = query.all()
            
        if category in CLIENT_CATEGORIES:
            all_matching = [c for c in all_matching if c.category == category]
            
        if membership_status != "all":
            today = datetime.now().date()
            if membership_status == "active":
                all_matching = [c for c in all_matching if any(m.end_date >= today for m in c.memberships)]
            elif membership_status == "expired":
                all_matching = [c for c in all_matching if c.memberships and all(m.end_date < today for m in c.memberships)]
            elif membership_status == "none":
                all_matching = [c for c in all_matching if not c.memberships]

        total_clients = len(all_matching)
        total_pages = math.ceil(total_clients / per_page)
        
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        clients_paginated = all_matching[start_idx:end_idx]
        
        return render_template("clients.html", 
                               clients=clients_paginated, 
                               categories=CLIENT_CATEGORIES,
                               category_label=category_label,
                               search_query=search_query,
                               selected_category=category,
                               membership_status=membership_status,
                               current_page=page,
                               total_pages=total_pages,
                               total_clients=total_clients)

    def post(self):
        db = g.db
        repo = ClientRepository(db)
        
        full_name = request.form.get("full_name", "").strip()
        phone = format_phone(request.form.get("phone", "").strip())
        email = request.form.get("email", "").strip()
        category = request.form.get("category", "client").strip()

        if not full_name or not phone or category not in CLIENT_CATEGORIES:
            flash("Заполните обязательные поля клиента.")
            return redirect(request.referrer or url_for("clients"))

        if repo.find_client_by_phone(phone):
            flash("Телефон уже существует.")
            return redirect(request.referrer or url_for("clients"))

        client = Client(full_name=full_name, phone=phone, email=email or None, category=category)
        repo.add_client(client)
        flash("Клиент добавлен.")
        return redirect(request.referrer or url_for("clients"))

class ClientProfileView(MethodView):
    decorators = [login_required]

    def get(self, client_id):
        db = g.db
        client = db.query(Client).get(client_id)
        if not client:
            flash("Клиент не найден.")
            return redirect(url_for("clients"))
            
        today = datetime.now().date()
        return render_template("client_profile.html", client=client, category_label=category_label, today=today)

class ClientDetailView(MethodView):
    decorators = [login_required]

    def post(self, client_id, action):
        db = g.db
        repo = ClientRepository(db)
        client = repo.get_client_by_id(client_id)
        
        if not client:
            flash("Клиент не найден.")
            return redirect(url_for("clients"))

        if action == "update":
            client.full_name = request.form.get("full_name", "").strip()
            client.phone = format_phone(request.form.get("phone", "").strip())
            client.email = request.form.get("email", "").strip() or None
            client.category = request.form.get("category", "client").strip()
            new_pin = request.form.get("new_pin", "").strip()
            if new_pin:
                if len(new_pin) < 4:
                    flash("PIN должен быть не короче 4 цифр.")
                    return redirect(request.referrer or url_for("client_profile", client_id=client_id))
                client.set_pin(new_pin)
            db.commit()
            flash("Клиент обновлен.")
        elif action == "delete":
            db.delete(client)
            db.commit()
            flash("Клиент удален.")
            return redirect(url_for("clients"))
            
        return redirect(request.referrer or url_for("clients"))

class ScheduleView(MethodView):
    decorators = [login_required]

    def get(self):
        db = g.db
        from models.trainer import Trainer
        from models.client import Client
        from models.session import ClassSession
        from datetime import datetime, timedelta
        
        week_offset = int(request.args.get('week_offset', 0))
        trainer_id_filter = request.args.get('trainer_id', '')
        client_id_filter = request.args.get('client_id', '')
        today = datetime.now().date()
        
        current_monday = today - timedelta(days=today.weekday())
        target_monday = current_monday + timedelta(weeks=week_offset)
        target_sunday = target_monday + timedelta(days=6)
        
        trainers = db.query(Trainer).all()
        clients = db.query(Client).all()
        
        query = db.query(ClassSession).filter(
            ClassSession.start_time >= target_monday,
            ClassSession.start_time < target_sunday + timedelta(days=1)
        )
        
        if trainer_id_filter and trainer_id_filter.isdigit():
            query = query.filter(ClassSession.trainer_id == int(trainer_id_filter))
            
        sessions = query.order_by(ClassSession.start_time).all()
        
        # Группируем по датам
        sessions_by_date = {}
        for s in sessions:
            d = s.start_time.date()
            if d not in sessions_by_date:
                sessions_by_date[d] = []
            sessions_by_date[d].append(s)
            
        # Алгоритм расчета коллизий
        START_HOUR = 8
        PIXELS_PER_MINUTE = 1
        layout_by_date = {}
        
        for d, day_sessions in sessions_by_date.items():
            clusters = []
            current_cluster = []
            cluster_end_time = None
            
            for session in day_sessions:
                s_start = session.start_time
                s_end = s_start + timedelta(minutes=session.duration_minutes)
                
                if not current_cluster:
                    current_cluster.append(session)
                    cluster_end_time = s_end
                else:
                    if s_start < cluster_end_time:
                        current_cluster.append(session)
                        if s_end > cluster_end_time:
                            cluster_end_time = s_end
                    else:
                        clusters.append(current_cluster)
                        current_cluster = [session]
                        cluster_end_time = s_end
            if current_cluster:
                clusters.append(current_cluster)
                
            layout_sessions = []
            for cluster in clusters:
                columns = []
                for session in cluster:
                    s_start = session.start_time
                    placed = False
                    for col_idx, col in enumerate(columns):
                        last_session = col[-1]
                        last_end = last_session.start_time + timedelta(minutes=last_session.duration_minutes)
                        if s_start >= last_end:
                            col.append(session)
                            session._col_idx = col_idx
                            placed = True
                            break
                    if not placed:
                        session._col_idx = len(columns)
                        columns.append([session])
                        
                num_columns = len(columns)
                width_pct = 100.0 / num_columns
                
                for session in cluster:
                    start_minutes = (session.start_time.hour - START_HOUR) * 60 + session.start_time.minute
                    top_px = start_minutes * PIXELS_PER_MINUTE
                    height_px = session.duration_minutes * PIXELS_PER_MINUTE
                    if top_px < 0: top_px = 0
                    
                    layout_sessions.append({
                        'session': session,
                        'top': top_px,
                        'height': height_px,
                        'left': session._col_idx * width_pct,
                        'width': width_pct
                    })
            layout_by_date[d] = layout_sessions
        
        return render_template(
            "schedule.html", 
            trainers=trainers, 
            clients=clients,
            layout_by_date=layout_by_date, 
            week_offset=week_offset,
            selected_trainer=trainer_id_filter,
            target_monday=target_monday,
            target_sunday=target_sunday,
            timedelta=timedelta,
            today=today
        )

    def post(self):
        db = g.db
        from models.session import ClassSession
        from datetime import datetime
        
        action = request.form.get('action')
        week_offset = request.form.get('week_offset', 0)
        selected_trainer = request.form.get('selected_trainer', '')
        
        if action == 'create':
            client_id = request.form.get('client_id')
            trainer_id = request.form.get('trainer_id')
            date_str = request.form.get('date')
            time_str = request.form.get('time')
            duration = request.form.get('duration_minutes', 60)
            title = request.form.get('title', '').strip()
            note = request.form.get('note', '').strip()
            
            if not title and client_id:
                title = "Персональная тренировка"
                
            if date_str and time_str and title:
                start_time = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                new_session = ClassSession(
                    title=title,
                    client_id=int(client_id) if client_id else None,
                    trainer_id=int(trainer_id) if trainer_id else None,
                    start_time=start_time,
                    duration_minutes=int(duration),
                    note=note
                )
                db.add(new_session)
                db.commit()
                flash("Занятие добавлено.")
            else:
                flash("Заполните обязательные поля.")
                
        elif action == 'delete':
            session_id = request.form.get('session_id')
            if session_id:
                session_obj = db.query(ClassSession).get(session_id)
                if session_obj:
                    db.delete(session_obj)
                    db.commit()
                    flash("Занятие удалено.")
                    
        # Перенаправляем обратно с сохранением смещения и фильтра
        return redirect(url_for('schedule', week_offset=week_offset, trainer_id=selected_trainer))

class TrainerView(MethodView):
    decorators = [login_required]

    def post(self):
        db = g.db
        full_name = request.form.get("full_name", "").strip()
        phone = format_phone(request.form.get("phone", "").strip())
        specialization = request.form.get("specialization", "").strip()
        
        if not full_name or not specialization or not phone:
            flash("Заполните данные тренера.")
            return redirect(request.referrer or url_for("index"))

        trainer = Trainer(full_name=full_name, phone=phone, specialization=specialization)
        db.add(trainer)
        db.commit()
        flash("Тренер добавлен.")
        return redirect(request.referrer or url_for("index"))

class TrainerDetailView(MethodView):
    decorators = [login_required]

    def post(self, trainer_id, action):
        db = g.db
        trainer = db.query(Trainer).get(trainer_id)
        
        if not trainer:
            flash("Тренер не найден.")
            return redirect(request.referrer or url_for("index"))

        if action == "update":
            trainer.full_name = request.form.get("full_name", "").strip()
            trainer.phone = format_phone(request.form.get("phone", "").strip())
            trainer.specialization = request.form.get("specialization", "").strip()
            db.commit()
            flash("Тренер обновлен.")
        elif action == "delete":
            db.delete(trainer)
            db.commit()
            flash("Тренер удален.")
            
        return redirect(request.referrer or url_for("index"))

class MembershipView(MethodView):
    decorators = [login_required]

    def post(self):
        db = g.db
        name = request.form.get("name", "").strip()
        duration_days = request.form.get("duration_days", "").strip()
        price = request.form.get("price", "").strip()
        
        if not name or not duration_days or not price:
            flash("Заполните все поля абонемента.")
            return redirect(request.referrer or url_for("index"))

        try:
            membership = Membership(name=name, duration_days=int(duration_days), price=float(price))
            db.add(membership)
            db.commit()
            flash("Тип абонемента добавлен.")
        except Exception:
            flash("Ошибка при добавлении абонемента.")
        return redirect(request.referrer or url_for("index"))

class MembershipDetailView(MethodView):
    decorators = [login_required]

    def post(self, membership_id, action):
        db = g.db
        membership = db.query(Membership).get(membership_id)
        
        if not membership:
            flash("Абонемент не найден.")
            return redirect(request.referrer or url_for("index"))

        if action == "update":
            membership.name = request.form.get("name", "").strip()
            membership.duration_days = int(request.form.get("duration_days", "0").strip())
            membership.price = float(request.form.get("price", "0").strip())
            db.commit()
            flash("Абонемент обновлен.")
        elif action == "delete":
            db.delete(membership)
            db.commit()
            flash("Абонемент удален.")
            
        return redirect(request.referrer or url_for("index"))

class AssignMembershipView(MethodView):
    decorators = [login_required]

    def post(self):
        db = g.db
        client_id = request.form.get("client_id", "").strip()
        membership_id = request.form.get("membership_id", "").strip()
        start_date_str = request.form.get("start_date", "").strip()
        
        if not client_id or not membership_id or not start_date_str:
            flash("Выберите клиента, абонемент и дату начала.")
            return redirect(request.referrer or url_for("index"))

        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Неверный формат даты начала.")
            return redirect(request.referrer or url_for("index"))
            
        client = db.query(Client).get(int(client_id))
        membership_type = db.query(Membership).get(int(membership_id))
        
        if not client or not membership_type:
            flash("Клиент или абонемент не найден.")
            return redirect(request.referrer or url_for("index"))
            
        service = MembershipService(db)
        service.assign_to_client(client, membership_type, start_date)
        flash("Абонемент назначен клиенту.")
        return redirect(request.referrer or url_for("index"))

class AttendanceCreateView(MethodView):
    decorators = [login_required]

    def post(self):
        db = g.db
        client_id = request.form.get("client_id", "").strip()
        trainer_id = request.form.get("trainer_id", "").strip()
        visit_date_str = request.form.get("visit_date", "").strip()
        
        if not client_id or not visit_date_str:
            flash("Выберите клиента и дату посещения.")
            return redirect(request.referrer or url_for("index"))

        try:
            visit_date = datetime.strptime(visit_date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Неверный формат даты посещения.")
            return redirect(request.referrer or url_for("index"))
            
        client = db.query(Client).get(int(client_id))
        trainer = db.query(Trainer).get(int(trainer_id)) if trainer_id else None
        
        if not client:
            flash("Клиент не найден.")
            return redirect(request.referrer or url_for("index"))
            
        today = datetime.now().date()
        message = "Вход в зал отмечен."
        warning = False
        service = AttendanceService(db)

        try:
            if visit_date == today:
                check_in(db, client, trainer, strict=True)
            else:
                visit = service.register_visit(client, visit_date, trainer, strict=True)
                visit.check_in_at = datetime.combine(visit_date, datetime.min.time())
                visit.check_out_at = visit.check_in_at
                db.commit()
                message = "Визит за прошедшую дату сохранён."
        except Exception as e:
            err = str(e)
            if "уже" in err.lower() and visit_date == today:
                if is_ajax_request():
                    return jsonify({"ok": False, "message": err}), 400
                flash(err)
                return redirect(request.referrer or url_for("index"))
            if "истек" in err.lower() or "абонемент" in err.lower():
                if visit_date == today:
                    check_in(db, client, trainer, strict=False)
                else:
                    visit = service.register_visit(client, visit_date, trainer, strict=False)
                    visit.check_in_at = datetime.combine(visit_date, datetime.min.time())
                    visit.check_out_at = visit.check_in_at
                    db.commit()
                message = f"Вход отмечен: у {client.full_name} нет активного абонемента."
                warning = True
            else:
                if is_ajax_request():
                    return jsonify({"ok": False, "message": err}), 400
                flash(err)
                return redirect(request.referrer or url_for("index"))

        visits_today, unique_today = visit_counts(db, today)
        in_gym = count_in_gym(db)

        if is_ajax_request():
            return jsonify({
                "ok": True,
                "warning": warning,
                "message": message,
                "client_name": client.full_name,
                "visits_today": visits_today,
                "unique_today": unique_today,
                "in_gym_count": in_gym,
                "visit_date": visit_date.strftime("%d.%m.%Y"),
            })

        flash(message)
        return redirect(request.referrer or url_for("index"))


class AttendanceCheckoutView(MethodView):
    decorators = [login_required]

    def post(self):
        db = g.db
        client_id = request.form.get("client_id", "").strip()
        if not client_id:
            flash("Выберите клиента.")
            return redirect(request.referrer or url_for("index"))

        client = db.query(Client).get(int(client_id))
        if not client:
            flash("Клиент не найден.")
            return redirect(request.referrer or url_for("index"))

        try:
            check_out(db, client)
            message = f"{client.full_name} покинул зал."
        except Exception as e:
            if is_ajax_request():
                return jsonify({"ok": False, "message": str(e)}), 400
            flash(str(e))
            return redirect(request.referrer or url_for("index"))

        today = datetime.now().date()
        if is_ajax_request():
            return jsonify({
                "ok": True,
                "message": message,
                "in_gym_count": count_in_gym(db),
                "visits_today": visit_counts(db, today)[0],
            })
        flash(message)
        return redirect(request.referrer or url_for("index"))


class ReportView(MethodView):
    decorators = [login_required]

    def post(self):
        db = g.db
        date_from = request.form.get("date_from", "").strip()
        date_to = request.form.get("date_to", "").strip()
        
        if not date_from or not date_to:
            flash("Укажите период отчета.")
            return redirect(request.referrer or url_for("index"))

        try:
            d_from = datetime.strptime(date_from, "%Y-%m-%d").date()
            d_to = datetime.strptime(date_to, "%Y-%m-%d").date()
        except ValueError:
            flash("Неверный формат даты в отчете.")
            return redirect(request.referrer or url_for("index"))
            
        data = get_dashboard_data(db)
        report_rows = db.query(Visit).filter(Visit.visit_date >= d_from, Visit.visit_date <= d_to).order_by(Visit.visit_date).all()
        period = f"{date_from} -> {date_to}"
        
        return render_template("dashboard.html", report_rows=report_rows, report_period=period, category_label=category_label, date_from=date_from, date_to=date_to, **data)
class ReportExportView(MethodView):
    decorators = [login_required]

    def get(self):
        db = g.db
        date_from = request.args.get("date_from", "").strip()
        date_to = request.args.get("date_to", "").strip()
        
        if not date_from or not date_to:
            flash("Укажите период для экспорта.", "error")
            return redirect(request.referrer or url_for("index"))

        try:
            d_from = datetime.strptime(date_from, "%Y-%m-%d").date()
            d_to = datetime.strptime(date_to, "%Y-%m-%d").date()
        except ValueError:
            flash("Неверный формат даты в отчете.", "error")
            return redirect(request.referrer or url_for("index"))

        visits = db.query(Visit).filter(Visit.visit_date >= d_from, Visit.visit_date <= d_to).order_by(Visit.visit_date).all()
        
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')
        writer.writerow(['Дата', 'Клиент', 'Категория', 'Тренер', 'Детали'])
        
        for v in visits:
            client_name = v.client.full_name
            category = category_label(v.client.category)
            trainer_name = v.trainer.full_name if v.trainer else 'Без тренера'
            note = v.note or '-'
            writer.writerow([v.visit_date.strftime("%Y-%m-%d"), client_name, category, trainer_name, note])
            
        csv_data = '\ufeff' + output.getvalue()
        
        response = make_response(csv_data)
        response.headers["Content-Disposition"] = f"attachment; filename=report_{date_from}_to_{date_to}.csv"
        response.headers["Content-type"] = "text/csv; charset=utf-8"
        return response

# Registering URLs
app.add_url_rule("/login", view_func=LoginView.as_view("login"))
app.add_url_rule("/logout", view_func=LogoutView.as_view("logout"))
app.add_url_rule("/", view_func=IndexView.as_view("index"))
app.add_url_rule("/clients", view_func=ClientListView.as_view("clients"))
app.add_url_rule("/clients/<int:client_id>", view_func=ClientProfileView.as_view("client_profile"))
app.add_url_rule("/clients/<int:client_id>/<action>", view_func=ClientDetailView.as_view("client_detail"))
app.add_url_rule("/schedule", view_func=ScheduleView.as_view("schedule"))
app.add_url_rule("/trainers", view_func=TrainerView.as_view("trainers"))
app.add_url_rule("/trainers/<int:trainer_id>/<action>", view_func=TrainerDetailView.as_view("trainer_detail"))
app.add_url_rule("/memberships", view_func=MembershipView.as_view("memberships"))
app.add_url_rule("/memberships/<int:membership_id>/<action>", view_func=MembershipDetailView.as_view("membership_detail"))
app.add_url_rule("/assign-membership", view_func=AssignMembershipView.as_view("assign_membership"))
app.add_url_rule("/attendance", view_func=AttendanceCreateView.as_view("attendance"))
app.add_url_rule("/attendance/checkout", view_func=AttendanceCheckoutView.as_view("attendance_checkout"))
app.add_url_rule("/report", view_func=ReportView.as_view("report"))
app.add_url_rule("/report/export", view_func=ReportExportView.as_view("report_export"))
app.add_url_rule("/admin/seed-demo", view_func=DemoSeedView.as_view("seed_demo"), methods=["POST"])

from member_portal import member_bp
app.register_blueprint(member_bp)

if __name__ == "__main__":
    app.run(debug=True, port=5001)
