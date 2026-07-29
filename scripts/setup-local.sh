#!/bin/bash
# Первоначальная настройка проекта на локальном компьютере
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== Lu4 Analytics — локальная установка ==="

# Проверка Docker
if ! command -v docker &>/dev/null; then
  echo "Ошибка: Docker не установлен."
  echo "Установите Docker Desktop: https://docs.docker.com/get-docker/"
  exit 1
fi

if ! docker compose version &>/dev/null; then
  echo "Ошибка: docker compose не найден."
  exit 1
fi

# .env
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Создан .env из .env.example — при необходимости измените JWT_SECRET и IMPORT_API_KEY"
else
  echo ".env уже существует"
fi

# Wiki-данные
if [ ! -d "$ROOT/data/wiki/library" ]; then
  echo "Ошибка: нет data/wiki/library"
  echo "Скопируйте wiki-данные в data/wiki/ и datasets в data/datasets/"
  exit 1
fi

# Сборка и запуск
echo ""
echo "Запуск Docker Compose (первый импорт wiki может занять несколько минут)..."
docker compose up -d --build --wait

echo ""
echo "============================================"
echo "  Приложение:  http://localhost"
echo "  API docs:    http://localhost/api/docs"
echo "  Логин:       admin / admin123"
echo "============================================"
