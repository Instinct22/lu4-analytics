"""Role permission keys and default matrix."""

from __future__ import annotations

ROLES = ("superadmin", "admin", "user", "driver", "other")

# Roles assignable via admin UI (superadmin may also assign admin)
ASSIGNABLE_ROLES = ("admin", "user", "driver", "other")

# Presets when creating a custom role (copy permissions from these)
PRESET_ROLES = ("admin", "user", "driver", "other")

SYSTEM_ROLES = frozenset(ROLES)

ROLE_LABELS = {
    "superadmin": "Суперадмин",
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
    "nav.trading",
    "nav.settings",
    "nav.admin",
    "feature.craft_prices",
    "feature.craft_bulk",
    "feature.craft_warehouse",
    "feature.raid_timers_view",
    "feature.raid_route",
    "feature.raid_timers_write",
    "feature.raid_visibility",
    "feature.trading_write",
    "feature.level_unrestricted",
    "admin.roles_manage",
    "admin.logs_view",
    "admin.users_quick_create",
    "admin.level_preset",
    "admin.level_restriction",
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
    "nav.trading": "Торговля (просмотр)",
    "nav.settings": "Настройки",
    "nav.admin": "Администрирование",
    "feature.craft_prices": "Цены в крафте",
    "feature.craft_bulk": "Доступ к мультикрафту",
    "feature.craft_warehouse": "Доступ к складу",
    "feature.raid_timers_view": "Доступ к таймерам РБ",
    "feature.raid_route": "Доступ к маршруту РБ",
    "feature.raid_timers_write": "Управление временем респа РБ",
    "feature.raid_visibility": "Настройка списка РБ",
    "feature.trading_write": "Торговля (редактирование)",
    "feature.level_unrestricted": "Уровни без ограничений",
    "admin.roles_manage": "Управление правами ролей",
    "admin.logs_view": "Журналы",
    "admin.users_quick_create": "Быстрое создание",
    "admin.level_preset": "Предустановка уровня",
    "admin.level_restriction": "Ограничение уровня",
}

DEFAULT_PUBLIC_ROLES: tuple[str, ...] = ("user", "driver", "other")

DEFAULT_PERMISSION_GROUPS: list[dict] = [
    {
        "id": "analytics",
        "label": "Аналитика",
        "permissions": ["nav.dashboard", "nav.charts", "nav.statistics"],
    },
    {
        "id": "raid",
        "label": "Рейд-боссы",
        "permissions": [
            "nav.raid_bosses",
            "feature.raid_timers_view",
            "feature.raid_route",
            "feature.raid_timers_write",
            "feature.raid_visibility",
            "feature.level_unrestricted",
        ],
    },
    {
        "id": "craft",
        "label": "Крафт",
        "permissions": [
            "nav.craft",
            "feature.craft_prices",
            "feature.craft_bulk",
            "feature.craft_warehouse",
        ],
    },
    {
        "id": "trading",
        "label": "Торговля",
        "permissions": ["nav.trading", "feature.trading_write"],
    },
    {
        "id": "administration",
        "label": "Администрирование",
        "permissions": ["nav.admin", "admin.users_quick_create", "admin.roles_manage", "admin.logs_view", "admin.level_preset", "admin.level_restriction"],
    },
]

_DRIVER_PERMS = frozenset({"nav.craft", "nav.items", "nav.character", "nav.settings"})
_ADMIN_ONLY = frozenset({"nav.admin", "admin.roles_manage", "admin.logs_view"})
_LEVEL_UNRESTRICTED = frozenset({"feature.level_unrestricted"})
# Shared clan inventory — grant explicitly in admin UI (not default user nav).
_TRADING_PERMS = frozenset({"nav.trading", "feature.trading_write"})

_USER_NAV = frozenset(
    p
    for p in PERMISSIONS
    if p not in _ADMIN_ONLY
    and not p.startswith("admin.")
    and p not in _LEVEL_UNRESTRICTED
    and p not in _TRADING_PERMS
)

DEFAULT_PERMISSIONS: dict[str, frozenset[str]] = {
    "superadmin": frozenset(PERMISSIONS),
    "admin": frozenset({"nav.admin", "admin.users_quick_create"}),
    "user": _USER_NAV,
    "driver": _DRIVER_PERMS | {"feature.craft_bulk", "feature.craft_warehouse"},
    "other": _DRIVER_PERMS | {"feature.craft_bulk", "feature.craft_warehouse"},
}


def is_superadmin(role: str) -> bool:
    return role == "superadmin"


def is_system_role(role: str) -> bool:
    return role in SYSTEM_ROLES


def default_allowed(role: str, permission: str) -> bool:
    return permission in DEFAULT_PERMISSIONS.get(role, frozenset())
