# arenda-site
# 🏗 Arenda Marketplace API

Backend для сервиса аренды вещей (дипломный проект).

## 🚀 Стек технологий

* Python 3.12
* Django + Django REST Framework
* PostgreSQL
* Redis (для WebSocket / чатов)
* Docker + Docker Compose
* Nginx
* Gunicorn

---

## 📦 Быстрый запуск через Docker

### 1️⃣ Клонировать репозиторий

```bash
git clone https://github.com/your-username/arenda-site.git
cd arenda-site
```

---

### 2️⃣ Создать `.env` файл (опционально)

```env
DEBUG=True
SECRET_KEY=your-secret-key
POSTGRES_DB=arenda
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

---

### 3️⃣ Запустить проект

```bash
docker-compose up --build
```

---

### 4️⃣ Выполнить миграции

В новом терминале:

```bash
docker-compose exec web python manage.py migrate
```

---

### 5️⃣ Создать суперпользователя

```bash
docker-compose exec web python manage.py createsuperuser
```

---

## 🌐 Доступ к API

После запуска:

```
http://localhost
```

Админка:

```
http://localhost/admin
```

---

## 📡 Основные API endpoints

### 📦 Items

```
GET    /api/items/
POST   /api/items/
GET    /api/items/{id}/
```

### 📅 Bookings

```
POST   /api/bookings/
POST   /api/bookings/{id}/confirm/
POST   /api/bookings/{id}/cancel/
```

### 💬 Chats

```
GET    /api/chats/conversations/
```

WebSocket:

```
ws://localhost/ws/chat/{conversation_id}/
```

### 🔔 Notifications

```
GET /api/notifications/
```

---

## 🧠 Особенности

* Пользователь не может бронировать свои товары
* Нельзя бронировать без заполненного профиля
* Автоматический расчёт стоимости аренды
* Рейтинг пользователей и товаров
* Чаты в реальном времени (WebSocket)
* Уведомления (сообщения, бронирования, отзывы)

---

## 🐳 Сервисы Docker

* `web` — Django приложение
* `db` — PostgreSQL
* `redis` — Redis (чаты)
* `nginx` — reverse proxy

---

## ⚙️ Полезные команды

Остановить контейнеры:

```bash
docker-compose down
```

Пересобрать:

```bash
docker-compose up --build
```

Войти в контейнер:

```bash
docker-compose exec web bash
```

---

## 🧪 Запуск тестов

```bash
docker-compose exec web python manage.py test
```

## ⚠️ Важно

Если не работает:

* проверь Docker Desktop запущен
* убедись что порт 8000 свободен
* попробуй `docker-compose down` и заново

---

