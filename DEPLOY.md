# Lu4 Analytics — перенос на сервер (без Git)

Сервер: **31.76.7.61** · каталог: **/opt/lu4-analytics**

---

## Что нужно на сервере

| | Минимум | Рекомендуется |
|--|---------|---------------|
| ОС | Debian 12 / Ubuntu 22.04+ | то же |
| RAM | **2 GB** | 4 GB |
| Диск | 10 GB свободно | 20+ GB |
| Порты | **80** (и 443 для HTTPS) | |

Git **не нужен**. Docker ставится скриптом `start.sh` автоматически.

> На 2 GB RAM скрипт сам создаст swap 2 GB и запустит backend с 1 worker.

---

## Шаг 1. Упаковать архив на Windows

Из корня проекта:

```powershell
cd f:\lu4_anal\lu4-analytics
.\scripts\pack-for-deploy.ps1
```

По умолчанию в архив входят **код + data** (wiki, datasets, raid-bosses).

Архив: `dist\lu4-analytics-YYYYMMDD-HHMM.tar.gz`

Опции:

```powershell
# Без data (только код) — данные копируете отдельно
.\scripts\pack-for-deploy.ps1 -NoData

# Без library\raw (~650 MB). Можно, если npc_loot уже импортирован на сервере
.\scripts\pack-for-deploy.ps1 -SkipRawHtml
```

### Что внутри архива

| Путь | Назначение |
|------|------------|
| `backend/`, `frontend/`, `database/`, `scripts/`, `nginx/` | Код (без node_modules, tests, кэшей) |
| `data/wiki/` | library + images |
| `data/datasets/` | JSON для импорта (encyclopedia, character, duals, raid bosses) |
| `data/raid-bosses/` | маршруты боссов |
| `docker-compose.prod.yml` | прод-стек |
| `.env.example` | шаблон секретов |
| `start.sh` | единый запуск |

**Не кладётся в архив:** `.env` (секреты только на сервере), `node_modules`, `dist`, кэши.

---

## Шаг 2. Скопировать архив на сервер

```powershell
scp "f:\lu4_anal\lu4-analytics\dist\lu4-analytics-YYYYMMDD-HHMM.tar.gz" root@31.76.7.61:/opt/
```

Подставьте реальное имя файла из `dist\`.

---

## Шаг 3. Разархивация с заменой старой версии

Обычный `tar xzf` поверх каталога **не удаляет** устаревшие файлы. Поэтому делаем чистую замену, сохраняя `.env` и БД (Docker volume `pgdata`).

```bash
ssh root@31.76.7.61
```

На сервере:

```bash
# 1. Остановить старый стек (volume БД не трогаем)
if [ -d /opt/lu4-analytics ]; then
  cd /opt/lu4-analytics
  docker compose -f docker-compose.prod.yml down 2>/dev/null || true
  docker compose -f docker-compose.yml down 2>/dev/null || true

  # 2. Сохранить секреты
  cp -a .env /tmp/lu4.env.bak 2>/dev/null || true

  # 3. Убрать старый каталог в бэкап
  cd /opt
  mv lu4-analytics "lu4-analytics.bak-$(date +%Y%m%d-%H%M)"
fi

# 4. Распаковать архив в чистый каталог
mkdir -p /opt/lu4-analytics
cd /opt/lu4-analytics
tar xzf /opt/lu4-analytics-*.tar.gz

# 5. Вернуть .env
if [ -f /tmp/lu4.env.bak ]; then
  cp -a /tmp/lu4.env.bak .env
else
  cp .env.example .env
fi
```

### Обязательно в `.env` (первый раз или если создали заново)

```bash
nano .env
```

```env
JWT_SECRET=<сгенерируйте: openssl rand -hex 32>
IMPORT_API_KEY=<другой: openssl rand -hex 32>
POSTGRES_PASSWORD=<надёжный пароль БД>
CORS_ORIGINS=http://31.76.7.61
SEED_USERS=admin:ваш_пароль_для_входа
UVICORN_WORKERS=1
HTTP_PORT=80
```

Сохранить в nano: `Ctrl+O` → Enter → `Ctrl+X`.

> Volume PostgreSQL (`pgdata`) живёт **вне** `/opt/lu4-analytics`. Замена файлов его не удаляет. Пароль `POSTGRES_PASSWORD` должен совпадать с тем, с которым volume был создан — иначе БД не поднимется. При смене пароля нужен `bash start.sh --fresh-db` (полная потеря данных БД).

---

## Шаг 4. Запуск

```bash
cd /opt/lu4-analytics
chmod +x start.sh scripts/*.sh
bash start.sh
```

Первый импорт wiki на 2 GB VPS: **10–15 минут**. Дождитесь:

```
Приложение:  http://31.76.7.61:80
```

### Флаги `start.sh`

| Команда | Когда |
|---------|--------|
| `bash start.sh` | обычный запуск / обновление кода |
| `bash start.sh --reimport-datasets` | обновили JSON в `data/datasets/` и нужно перелить в БД |
| `bash start.sh --fresh-db` | стереть БД и импортировать с нуля |

---

## Шаг 5. Проверка

```bash
curl http://localhost/api/health
docker compose -f docker-compose.prod.yml ps
```

В браузере: **http://31.76.7.61**

| URL | Что это |
|-----|---------|
| http://31.76.7.61/ | Веб-приложение |
| http://31.76.7.61/api/docs | Swagger API |
| Логин | из `SEED_USERS` в `.env` |

После успеха можно освободить диск:

```bash
rm -rf /opt/lu4-analytics.bak-*
rm -f /opt/lu4-analytics-*.tar.gz
docker system prune -f
```

---

## Firewall

```bash
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

---

## Обновление (следующий раз)

На Windows:

```powershell
cd f:\lu4_anal\lu4-analytics
.\scripts\pack-for-deploy.ps1
scp dist\lu4-analytics-*.tar.gz root@31.76.7.61:/opt/
```

На сервере — снова **шаг 3** (замена каталога с сохранением `.env`) и:

```bash
cd /opt/lu4-analytics
bash start.sh
```

Если обновили только датасеты:

```bash
bash start.sh --reimport-datasets
```

---

## Полезные команды

```bash
ssh root@31.76.7.61
cd /opt/lu4-analytics

docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml restart
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml exec backend python /scripts/import_wiki.py --if-empty
```

---

## Если OOM / мало памяти

```bash
free -h
grep UVICORN_WORKERS .env
bash start.sh
```

---

## Частые проблемы

| Проблема | Решение |
|----------|---------|
| `scp` / `ssh` не найдены | Включить «OpenSSH Client» в компонентах Windows |
| `502 Bad Gateway` | Подождите импорт; `docker compose -f docker-compose.prod.yml logs -f backend` |
| Нет картинок | Проверьте `data/wiki/images/` |
| Порт 80 занят | В `.env`: `HTTP_PORT=8080` или остановите чужой контейнер |
| Сборка Killed | Нужен swap — запускайте от root: `bash start.sh` |
| БД не стартует после смены пароля | Верните старый `POSTGRES_PASSWORD` или `bash start.sh --fresh-db` |
| Старые файлы остались после tar | Делайте чистую замену (шаг 3), не распаковывайте поверх |

---

## Чеклист безопасности

- [ ] Сменили `JWT_SECRET`, `IMPORT_API_KEY`, `POSTGRES_PASSWORD`
- [ ] Сменили пароль admin в `SEED_USERS`
- [ ] Сменили пароль root на сервере
- [ ] Включили `ufw`
- [ ] PostgreSQL не открыт наружу
- [ ] Реальный `.env` не кладёте в архив и не коммитите
