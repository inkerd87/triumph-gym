# Как выложить «Триумф» в интернет

Нужны три вещи: **хостинг** (сервер), **база PostgreSQL** и **секретные ключи** в настройках.

## Вариант 1 — Render (проще всего, есть бесплатный тариф)

1. Залейте проект на **GitHub** (репозиторий без `.venv` и без `.env`).

2. Зайдите на [render.com](https://render.com) → **New** → **PostgreSQL** → создайте базу `fitness_db`.

3. **New** → **Web Service** → подключите репозиторий:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command** (обязательно именно так, не `app:app`):  
     `gunicorn web_app:app --bind 0.0.0.0:$PORT`

   > Ошибка `Failed to find attribute 'app' in 'app'` — в Start Command указан неверный модуль. Нужен **web_app:app**, потому что Flask-приложение в файле `web_app.py`.

4. В **Environment** добавьте:

   | Переменная | Значение |
   |------------|----------|
   | `DATABASE_URL` | Internal Database URL из шага 2 |
   | `FLASK_SECRET_KEY` | длинная случайная строка (например из генератора паролей) |
   | `TRIUMPH_ADMIN_LOGIN` | логин админки |
   | `TRIUMPH_ADMIN_PASSWORD` | надёжный пароль (не `admin123`) |

5. Нажмите **Deploy**. Через несколько минут получите адрес вида  
   `https://triumph-xxxx.onrender.com`

6. Откройте в браузере:
   - админка: `https://ваш-домен/login`
   - кабинет участников: `https://ваш-домен/app/`

7. **Демо-данные в БД** (см. раздел «Временные данные» ниже).

На бесплатном тарифе сервис «засыпает» без посещений — первый заход может быть медленным.

---

## Вариант 2 — Railway или Fly.io

Та же схема: репозиторий → сервис Python → PostgreSQL → переменные `DATABASE_URL` и `FLASK_SECRET_KEY` → команда запуска из `Procfile`.

---

## Вариант 3 — VPS (Timeweb, Selectel, DigitalOcean)

На сервере с Ubuntu:

```bash
sudo apt update
sudo apt install python3-pip python3-venv nginx postgresql

# база
sudo -u postgres createdb fitness_db
sudo -u postgres createuser triumph -P

cd /var/www/triumph
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export DATABASE_URL=postgresql://triumph:ПАРОЛЬ@localhost:5432/fitness_db
export FLASK_SECRET_KEY=случайная_строка
export TRIUMPH_ADMIN_PASSWORD=надёжный_пароль

python web_app.py   # один раз — создаст таблицы, или просто запустите gunicorn
```

Запуск через systemd + gunicorn:

```ini
# /etc/systemd/system/triumph.service
[Service]
WorkingDirectory=/var/www/triumph
Environment="DATABASE_URL=postgresql://..."
Environment="FLASK_SECRET_KEY=..."
ExecStart=/var/www/triumph/.venv/bin/gunicorn web_app:app --bind 127.0.0.1:8000
```

Nginx проксирует 80/443 → `127.0.0.1:8000`, SSL — **Certbot** (Let's Encrypt).

---

## Временные (демо) данные в БД

Скрипты: `populate_db.py` и `populate_schedule.py`.

**Внимание:** `populate_db.py` **удаляет** клиентов, тренеров, абонементы и визиты, затем заливает новые. Админку не трогает.

### Способ 1 — с вашего Mac (бесплатно, Shell не нужен)

1. Render → **PostgreSQL** → **Connections** → скопируйте **External Database URL**  
   (не Internal — он только внутри Render).

2. В терминале на Mac:

```bash
cd /Users/elizaveta/folder

# На Mac часто нет команд python/pip — используйте venv напрямую:
.venv/bin/pip install -r requirements.txt

export DATABASE_URL="вставьте_External_Database_URL_сюда"

.venv/bin/python populate_db.py
.venv/bin/python populate_schedule.py
```

Если `.venv` нет — создайте: `python3 -m venv .venv`, затем команды выше.

**Ошибка `psycopg2` / `library load disallowed by system policy` на Mac:**

```bash
cd /Users/elizaveta/folder
xattr -cr .venv
.venv/bin/python3 -m pip install --force-reinstall --no-cache-dir psycopg2-binary
```

Потом снова `populate_db.py` и `populate_schedule.py`.

Если ругается на SSL, добавьте в конец URL: `?sslmode=require`

Данные попадут в ту же базу, что использует сайт на Render.

### Способ 2 — кнопка в админке (без Shell)

1. Render → Web Service → **Environment** → добавьте:  
   `ALLOW_DEMO_SEED` = `1`
2. **Save** → дождитесь перезапуска.
3. Войдите в админку на сайте → на главной появится **«Загрузить демо-данные»** → нажмите.
4. **Обязательно удалите** `ALLOW_DEMO_SEED` после заливки (чтобы никто посторонний не нажал снова).

Нужен деплой с последним кодом (`git push`, если кнопки ещё нет).

### Способ 3 — Render Shell (платно на некоторых тарифах)

```bash
python populate_db.py
python populate_schedule.py
```

### Локально (только своя БД на Mac)

```bash
cd /Users/elizaveta/folder
source .venv/bin/activate
export DATABASE_URL=postgresql://ваш_логин@localhost:5432/fitness_db

python populate_db.py
python populate_schedule.py
```

### Вход после демо-данных

| Куда | Логин | Пароль / PIN |
|------|--------|----------------|
| Админка `/login` | `admin` (или `TRIUMPH_ADMIN_LOGIN`) | `admin123` или ваш `TRIUMPH_ADMIN_PASSWORD` |
| Кабинет `/app/` | телефон клиента, напр. `+7 900 123-45-67` | **последние 4 цифры** номера → `4567` |

Примеры клиентов из `populate_db.py`: Иван Иванов, Екатерина Кузнецова, Александр Соколов и др.

---

## Локально перед выкладкой

```bash
cd /Users/elizaveta/folder
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export FLASK_SECRET_KEY=test-secret
export DATABASE_URL=postgresql://...@localhost:5432/fitness_db
gunicorn web_app:app --bind 0.0.0.0:8000
```

Проверка: http://127.0.0.1:8000 и http://127.0.0.1:8000/app/

**Не используйте** `python web_app.py` в продакшене — там `debug=True`, это только для разработки.

---

## Чеклист безопасности

- [ ] Сменить пароль админа (`TRIUMPH_ADMIN_PASSWORD`)
- [ ] Задать `FLASK_SECRET_KEY`
- [ ] Не коммитить `.env` в Git
- [ ] PostgreSQL только с паролем, не открывать порт 5432 в интернет без firewall

---

## Свой домен (например triumph-gym.ru)

В панели хостинга (Render / Cloudflare / регистратор) добавьте **CNAME** на адрес сервиса. В Render: Settings → Custom Domain.
