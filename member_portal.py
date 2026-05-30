"""Личный кабинет участника зала «Триумф» (/app)."""

import re
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Blueprint,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask.views import MethodView
from sqlalchemy.orm import joinedload

from models.client import Client
from models.membership import ClientMembership
from models.session import ClassSession
from models.visit import Visit
from repositories.client_repository import ClientRepository
from services.gym_presence import check_in, check_out, count_in_gym, get_open_visit
from services.gym_equipment import equipment_with_labels, equipment_zones

member_bp = Blueprint(
    'member',
    __name__,
    url_prefix='/app',
    template_folder='templates/member',
)


def member_login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get('client_id'):
            return redirect(url_for('member.login'))
        return view_func(*args, **kwargs)
    return wrapped


def get_current_client(db):
    return (
        db.query(Client)
        .options(
            joinedload(Client.memberships).joinedload(ClientMembership.membership),
            joinedload(Client.visits),
        )
        .get(session.get('client_id'))
    )


def find_client_by_phone(db, phone_raw: str):
    from helpers import format_phone

    repo = ClientRepository(db)
    formatted = format_phone(phone_raw.strip())
    if formatted:
        client = repo.find_client_by_phone(formatted)
        if client:
            return client
    digits = re.sub(r'\D', '', phone_raw)
    if len(digits) < 10:
        return None
    tail = digits[-10:]
    for client in db.query(Client).all():
        c_digits = re.sub(r'\D', '', client.phone or '')
        if c_digits.endswith(tail):
            return client
    return None


def active_membership(client, today):
    active = [
        m for m in client.memberships
        if m.start_date <= today <= m.end_date
    ]
    if not active:
        return None
    return max(active, key=lambda m: m.end_date)


def member_category_label(category):
    return {'client': 'Стандарт', 'vip': 'VIP', 'trainer': 'Тренер'}.get(category, 'Участник')


def get_member_schedule(db, week_offset=0):
    today = datetime.now().date()
    current_monday = today - timedelta(days=today.weekday())
    target_monday = current_monday + timedelta(weeks=week_offset)
    target_sunday = target_monday + timedelta(days=6)

    sessions = (
        db.query(ClassSession)
        .options(joinedload(ClassSession.trainer), joinedload(ClassSession.client))
        .filter(
            ClassSession.start_time >= datetime.combine(target_monday, datetime.min.time()),
            ClassSession.start_time < datetime.combine(target_sunday + timedelta(days=1), datetime.min.time()),
        )
        .order_by(ClassSession.start_time)
        .all()
    )

    days = []
    day_names = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    for i in range(7):
        d = target_monday + timedelta(days=i)
        day_sessions = [s for s in sessions if s.start_time.date() == d]
        days.append({
            'date': d,
            'label': day_names[i],
            'is_today': d == today,
            'sessions': day_sessions,
        })

    return {
        'days': days,
        'target_monday': target_monday,
        'target_sunday': target_sunday,
        'week_offset': week_offset,
    }


class MemberLoginView(MethodView):
    def get(self):
        if session.get('client_id'):
            return redirect(url_for('member.home'))
        return render_template('member/login.html')

    def post(self):
        db = g.db
        phone = request.form.get('phone', '').strip()
        pin = request.form.get('pin', '').strip()
        if not phone or not pin:
            flash('Введите телефон и PIN-код.')
            return redirect(url_for('member.login'))

        client = find_client_by_phone(db, phone)
        if not client or not client.check_pin(pin):
            flash('Неверный телефон или PIN.')
            return redirect(url_for('member.login'))

        session['client_id'] = client.id
        session['client_name'] = client.full_name
        return redirect(url_for('member.home'))


class MemberLogoutView(MethodView):
    def post(self):
        session.pop('client_id', None)
        session.pop('client_name', None)
        return redirect(url_for('member.login'))


class MemberHomeView(MethodView):
    decorators = [member_login_required]

    def get(self):
        db = g.db
        client = get_current_client(db)
        if not client:
            session.clear()
            return redirect(url_for('member.login'))

        today = datetime.now().date()
        month_start = today.replace(day=1)
        visits_month = (
            db.query(Visit)
            .filter(Visit.client_id == client.id, Visit.visit_date >= month_start)
            .count()
        )
        membership = active_membership(client, today)
        days_left = (membership.end_date - today).days if membership else 0
        total_days = 0
        if membership and membership.membership:
            total_days = membership.membership.duration_days or 1
        progress = min(100, max(0, int(days_left / total_days * 100))) if membership and total_days else 0

        upcoming = (
            db.query(ClassSession)
            .options(joinedload(ClassSession.trainer))
            .filter(ClassSession.start_time >= datetime.now())
            .order_by(ClassSession.start_time)
            .limit(3)
            .all()
        )

        open_visit = get_open_visit(db, client.id)

        return render_template(
            'member/home.html',
            client=client,
            today=today,
            membership=membership,
            days_left=days_left,
            progress=progress,
            visits_month=visits_month,
            upcoming=upcoming,
            category_label=member_category_label,
            in_gym_count=count_in_gym(db),
            is_in_gym=open_visit is not None,
            open_visit=open_visit,
        )


class MemberGymStatusView(MethodView):
    decorators = [member_login_required]

    def get(self):
        db = g.db
        client = get_current_client(db)
        open_visit = get_open_visit(db, client.id) if client else None
        return jsonify({
            'in_gym_count': count_in_gym(db),
            'is_in_gym': open_visit is not None,
        })


class MemberCheckInView(MethodView):
    decorators = [member_login_required]

    def post(self):
        db = g.db
        client = get_current_client(db)
        try:
            check_in(db, client, strict=True)
            msg = 'Добро пожаловать в зал!'
        except Exception as e:
            err = str(e)
            if 'уже' in err.lower():
                return jsonify({'ok': False, 'message': err}), 400
            if 'истек' in err.lower() or 'абонемент' in err.lower():
                check_in(db, client, strict=False)
                msg = 'Вход отмечен. Абонемент не активен — уточните на ресепшене.'
            else:
                return jsonify({'ok': False, 'message': err}), 400
        return jsonify({
            'ok': True,
            'message': msg,
            'in_gym_count': count_in_gym(db),
            'is_in_gym': True,
        })


class MemberCheckOutView(MethodView):
    decorators = [member_login_required]

    def post(self):
        db = g.db
        client = get_current_client(db)
        try:
            check_out(db, client)
        except Exception as e:
            return jsonify({'ok': False, 'message': str(e)}), 400
        return jsonify({
            'ok': True,
            'message': 'До встречи! Хорошей тренировки была.',
            'in_gym_count': count_in_gym(db),
            'is_in_gym': False,
        })


class MemberScheduleView(MethodView):
    decorators = [member_login_required]

    def get(self):
        db = g.db
        client = get_current_client(db)
        week_offset = int(request.args.get('week_offset', 0))
        schedule = get_member_schedule(db, week_offset)
        return render_template(
            'member/schedule.html',
            client=client,
            **schedule,
        )


class MemberEquipmentView(MethodView):
    decorators = [member_login_required]

    def get(self):
        return render_template(
            'member/equipment.html',
            equipment=equipment_with_labels(),
            equipment_zones=equipment_zones(),
        )


class MemberProfileView(MethodView):
    decorators = [member_login_required]

    def get(self):
        db = g.db
        client = get_current_client(db)
        today = datetime.now().date()
        visits = (
            db.query(Visit)
            .options(joinedload(Visit.trainer))
            .filter(Visit.client_id == client.id)
            .order_by(Visit.visit_date.desc())
            .limit(20)
            .all()
        )
        memberships = sorted(client.memberships, key=lambda m: m.end_date, reverse=True)
        return render_template(
            'member/profile.html',
            client=client,
            today=today,
            visits=visits,
            memberships=memberships,
            category_label=member_category_label,
        )

    def post(self):
        db = g.db
        client = get_current_client(db)
        current_pin = request.form.get('current_pin', '').strip()
        new_pin = request.form.get('new_pin', '').strip()
        confirm_pin = request.form.get('confirm_pin', '').strip()

        if not client.check_pin(current_pin):
            flash('Текущий PIN неверный.')
            return redirect(url_for('member.profile'))
        if len(new_pin) < 4:
            flash('Новый PIN — минимум 4 цифры.')
            return redirect(url_for('member.profile'))
        if new_pin != confirm_pin:
            flash('PIN-коды не совпадают.')
            return redirect(url_for('member.profile'))

        client.set_pin(new_pin)
        db.commit()
        flash('PIN успешно изменён.')
        return redirect(url_for('member.profile'))


member_bp.add_url_rule('/login', view_func=MemberLoginView.as_view('login'), methods=['GET', 'POST'])
member_bp.add_url_rule('/logout', view_func=MemberLogoutView.as_view('logout'), methods=['POST'])
member_bp.add_url_rule('/', view_func=MemberHomeView.as_view('home'))
member_bp.add_url_rule('/schedule', view_func=MemberScheduleView.as_view('schedule'))
member_bp.add_url_rule('/equipment', view_func=MemberEquipmentView.as_view('equipment'))
member_bp.add_url_rule('/profile', view_func=MemberProfileView.as_view('profile'), methods=['GET', 'POST'])
member_bp.add_url_rule('/api/gym-status', view_func=MemberGymStatusView.as_view('gym_status'))
member_bp.add_url_rule('/checkin', view_func=MemberCheckInView.as_view('checkin'), methods=['POST'])
member_bp.add_url_rule('/checkout', view_func=MemberCheckOutView.as_view('checkout'), methods=['POST'])
