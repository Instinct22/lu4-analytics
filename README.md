# Lu4 Analytics Platform

Информационно-аналитическая система для Lu4 Wiki: библиотека знаний, рыночная аналитика, craft/character калькуляторы.

## Стек

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL
- **Frontend:** React, TypeScript, Vite, TanStack Query, TailwindCSS, Recharts
- **Infra:** Docker Compose, Nginx

## Структура проекта

```
server/
├── backend/           # FastAPI: api → services → models
│   ├── api/
│   ├── services/
│   ├── calculations/
│   ├── core/
│   └── tests/
├── frontend/          # React SPA
├── database/          # Alembic миграции
├── scripts/
├── nginx/
├── data/
│   ├── wiki/          # library/ + images/ (runtime)
│   ├── datasets/      # craft/character JSON для import
│   └── media/         # загружаемые файлы
└── docker-compose.yml
```

### Runtime-данные

| Путь | Env | Зачем |
|------|-----|--------|
| `data/wiki/` | `WIKI_PATH` | `library/` (import + NPC loot raw HTML), `images/` (иконки) |
| `data/datasets/` | `DATASETS_PATH` | craft/character analytics JSON |
| `data/media/` | `MEDIA_PATH` | uploads |

Scrape-скрипты и отчёты (`.py`, `.xlsx`, `.html`) в runtime **не нужны** — живут только в offline-пайплайне `chat_bot/` (вне `server/`).

### Offline datasets (items encyclopedia)

`items_encyclopedia.json` — единственный источник для предметов, крафта и источников
ресурсов. После обновления wiki library пересоберите его до импорта:

```bash
# В Docker (рекомендуется — в backend уже есть beautifulsoup4):
docker compose exec backend python /scripts/build_craft_catalog.py
docker compose exec backend python /scripts/build_items_encyclopedia.py
docker compose exec backend python /scripts/import_datasets.py items_encyclopedia

# Локально (нужен pip install -r backend/requirements.txt):
py -3 scripts/build_craft_catalog.py
py -3 scripts/build_items_encyclopedia.py
py -3 scripts/import_datasets.py items_encyclopedia
```

[`scripts/build_craft_catalog.py`](scripts/build_craft_catalog.py) читает `data/wiki/library/raw/lu4/item/*.html`, собирает `items`, `byProduct`, `sets` и **автоматически** выставляет категории (в т.ч. `Armor / Robe` → `armors/magic`) через [`scripts/craft_catalog/categories.py`](scripts/craft_catalog/categories.py). Его вывод
`craft_catalog.json` — промежуточный вход для `build_items_encyclopedia.py`, в базу
он больше не импортируется.

Доступные ключи для `import_datasets.py`: `items_encyclopedia`, `character`,
`duals_catalog`, `raid_bosses`. Без аргументов импортируются все.

---

## Локальный запуск

### Требования

- Docker Desktop (или Docker Engine + Compose v2)
- Git

### Установка

```bash
cp .env.example .env
# Положите wiki-данные в data/wiki/ и datasets в data/datasets/
bash scripts/setup-local.sh
```

Или вручную:

```bash
docker compose up -d --build --wait
```

### Доступ

| URL | Описание |
|-----|----------|
| http://localhost | Приложение |
| http://localhost/api/docs | Swagger |
| `admin` / `admin123` | из `SEED_USERS` |

```bash
docker compose ps
docker compose logs -f backend
cd backend && PYTHONPATH=. pytest tests/ -v
```

---

## API (кратко)

Auth: `/api/auth/*`  
Ingest: `/api/import`, `/api/market/scan`  
Wiki: `/api/wiki/entities/{id}`, `/api/wiki/npc/{id}/loot`  
Market: `/api/market/*`  
Search / stats: `/api/search`, `/api/statistics/*`  
Крафт: `/api/craft/catalog`, `/api/craft/recipes/{id}`, `/api/craft/resources*`, `/api/craft/profitability`  
Справочники: `/api/character/*`, `/api/duals/catalog`, `/api/raid/bosses`, `/api/raid/timers`  
Состояние пользователя: `/api/me/preferences/{scope}`

---

## База данных

- `wiki_entities` (materials в JSONB), `entity_links`, `market_records`, `item_statistics`
- Справочники из датасетов: `craft_items`, `craft_recipes`, `craft_recipe_materials`,
  `craft_material_sources`, `character_races`, `character_classes`, `character_skills`,
  `raid_bosses`, `raid_boss_timers`, `npc_loot`
- `user_preferences` — склад, ручные цены и выбранные варианты рецептов
- `analytics_datasets` — только небольшие блобы: конфиг карты боссов, каталог дуалов
  и `*_meta` (категории, сеты, счётчики)

Миграции: `001` → `013`.

---

## Разработка без Docker

```bash
cd backend && pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg2://lu4:lu4secret@localhost:5432/lu4
export WIKI_PATH=../data/wiki
export DATASETS_PATH=../data/datasets
cd ../database && alembic upgrade head
python ../scripts/seed_users.py
python ../scripts/import_wiki.py
cd ../backend && PYTHONPATH=. uvicorn main:app --reload

cd frontend && npm install && npm run dev
```
