"""Role permission keys and default matrix."""

from __future__ import annotations

ROLES = ("admin", "user", "driver", "other")

ROLE_LABELS = {
    "admin": "Админ",
    "user": "Пользователь",
    "driver": "Драйвер",
    "other": "Другое",
}

PERMISSIONS = (
    "nav.dashboard",
    "nav.charts",
    "nav.statistics",
    "nav.craft",
    "nav.items",
    "nav.character",
    "nav.resources",
    "nav.search",
    "nav.raid_bosses",
    "nav.admin",
    "feature.craft_prices",
    "feature.raid_timers_write",
)

PERMISSION_LABELS = {
    "nav.dashboard": "Dashboard",
    "nav.charts": "Графики",
    "nav.statistics": "Статистика",
    "nav.craft": "Крафт",
    "nav.items": "Предметы",
    "nav.character": "Персонаж",
    "nav.resources": "Ресурсы",
    "nav.search": "Поиск",
    "nav.raid_bosses": "Рейд Боссы",
    "nav.admin": "Администрирование",
    "feature.craft_prices": "Цены в крафте",
    "feature.raid_timers_write": "Таймеры рейд-боссов: запись",
}

# Defaults: Admin — всё; User — всё кроме админки; Driver/Other — крафт + предметы + дуалы + персонаж
_DRIVER_PERMS = frozenset({"nav.craft", "nav.items", "nav.character"})
_ADMIN_ONLY = frozenset({"nav.admin"})

DEFAULT_PERMISSIONS: dict[str, frozenset[str]] = {
    "admin": frozenset(PERMISSIONS),
    "user": frozenset(p for p in PERMISSIONS if p not in _ADMIN_ONLY),
    "driver": _DRIVER_PERMS,
    "other": _DRIVER_PERMS,
}


def default_allowed(role: str, permission: str) -> bool:
    return permission in DEFAULT_PERMISSIONS.get(role, frozenset())
