import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { usePreferencesSyncState } from "../hooks/usePreferences";
import { Suspense, useEffect, useMemo, useState } from "react";
import { LoadingState } from "../components/ui";

type NavLinkItem = {
  to: string;
  label: string;
  icon: string;
  permission: string;
  end?: boolean;
};

type NavGroup = {
  id: string;
  label: string;
  icon: string;
  children: NavLinkItem[];
  isActive?: (pathname: string) => boolean;
};

const analyticsGroup: NavGroup = {
  id: "analytics",
  label: "Аналитика",
  icon: "◈",
  children: [
    { to: "/", label: "Dashboard", icon: "◈", permission: "nav.dashboard", end: true },
    { to: "/charts", label: "Графики", icon: "◉", permission: "nav.charts" },
    { to: "/statistics", label: "Статистика", icon: "▤", permission: "nav.statistics" },
  ],
  isActive: (pathname) =>
    pathname === "/" || pathname === "/charts" || pathname === "/statistics",
};

const craftGroup: NavGroup = {
  id: "craft",
  label: "Крафт",
  icon: "⚒",
  children: [
    { to: "/craft", label: "Крафт предметов", icon: "⚒", permission: "nav.craft", end: true },
    { to: "/craft/bulk?tab=warehouse", label: "Склад", icon: "▦", permission: "nav.craft" },
  ],
  isActive: (pathname) => pathname.startsWith("/craft"),
};

const topLevelLinks: NavLinkItem[] = [
  { to: "/items", label: "Предметы", icon: "▣", permission: "nav.items" },
  { to: "/character", label: "Персонаж", icon: "⚔", permission: "nav.character" },
  { to: "/resources", label: "Ресурсы", icon: "◆", permission: "nav.resources" },
  { to: "/search", label: "Поиск", icon: "⌕", permission: "nav.search" },
  { to: "/raid-bosses", label: "Рейд Боссы", icon: "⚑", permission: "nav.raid_bosses" },
  { to: "/admin", label: "Администрирование", icon: "⚙", permission: "nav.admin" },
];

const ROLE_LABELS: Record<string, string> = {
  admin: "Админ",
  user: "Пользователь",
  driver: "Драйвер",
  other: "Другое",
};

function SidebarNavGroup({
  group,
  items,
  open,
  onToggle,
  active,
}: {
  group: NavGroup;
  items: NavLinkItem[];
  open: boolean;
  onToggle: () => void;
  active: boolean;
}) {
  const location = useLocation();
  if (items.length === 0) return null;

  return (
    <div className="space-y-1">
      <button
        type="button"
        onClick={onToggle}
        className={[
          "group flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200",
          active
            ? "bg-amber-500/10 text-amber-400 ring-1 ring-amber-500/20 shadow-sm"
            : "text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-200",
        ].join(" ")}
      >
        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-zinc-800/80 text-xs text-inherit opacity-70 transition-opacity group-hover:opacity-100">
          {group.icon}
        </span>
        <span className="flex-1 text-left">{group.label}</span>
        <span className={`text-xs transition-transform ${open ? "rotate-90" : ""}`}>›</span>
      </button>
      {open && (
        <div className="ml-3 space-y-1 border-l border-zinc-800/80 pl-2">
          {items.map((l) => {
            const path = l.to.split("?")[0];
            return (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              className={({ isActive }) => {
                const active = l.end ? isActive : isActive || location.pathname === path;
                return [
                  "group flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition-all duration-200",
                  active
                    ? "bg-amber-500/10 text-amber-400 ring-1 ring-amber-500/20 shadow-sm"
                    : "text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-200",
                ].join(" ");
              }}
            >
              <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-zinc-800/80 text-[0.65rem] text-inherit opacity-70 transition-opacity group-hover:opacity-100">
                {l.icon}
              </span>
              {l.label}
            </NavLink>
            );
          })}
        </div>
      )}
    </div>
  );
}

function useNavGroup(group: NavGroup, hasPermission: (p: string) => boolean) {
  const location = useLocation();
  const visibleChildren = group.children.filter((l) => hasPermission(l.permission));
  const active = useMemo(
    () => group.isActive?.(location.pathname) ?? visibleChildren.some((l) => location.pathname === l.to),
    [group, location.pathname, visibleChildren],
  );
  const [open, setOpen] = useState(active);

  useEffect(() => {
    if (active) setOpen(true);
  }, [active]);

  return { visibleChildren, active, open, setOpen };
}

export default function MainLayout() {
  const { user, logout, hasPermission } = useAuth();
  const { saveError } = usePreferencesSyncState();
  const navigate = useNavigate();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);

  const analytics = useNavGroup(analyticsGroup, hasPermission);
  const craft = useNavGroup(craftGroup, hasPermission);
  const visibleTopLevelLinks = topLevelLinks.filter((l) => hasPermission(l.permission));

  useEffect(() => {
    document.documentElement.classList.add("dark");
  }, []);

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  return (
    <div className="flex min-h-screen bg-surface bg-mesh-dark">
      {menuOpen && (
        <div
          role="presentation"
          onClick={() => setMenuOpen(false)}
          className="fixed inset-0 z-30 bg-black/70 backdrop-blur-sm lg:hidden"
        />
      )}

      <aside
        className={[
          "fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-zinc-800/80 bg-zinc-950/95 backdrop-blur-xl transition-transform duration-200",
          "lg:static lg:z-auto lg:w-64 lg:shrink-0 lg:translate-x-0 lg:bg-zinc-950/80",
          menuOpen ? "translate-x-0" : "-translate-x-full",
        ].join(" ")}
      >
        <div className="flex items-center justify-between gap-3 border-b border-zinc-800/80 px-6 py-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-amber-400 to-amber-600 shadow-glow">
              <span className="text-sm font-black text-zinc-950">L4</span>
            </div>
            <div>
              <h1 className="text-sm font-semibold tracking-tight text-zinc-50">Lu4 Analytics</h1>
              <p className="text-[0.7rem] text-zinc-500">Рынок и крафт</p>
            </div>
          </div>
          <button
            type="button"
            aria-label="Закрыть меню"
            onClick={() => setMenuOpen(false)}
            className="rounded-lg px-2 py-1 text-lg text-zinc-500 transition-colors hover:bg-zinc-800 hover:text-zinc-200 lg:hidden"
          >
            ✕
          </button>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto p-4">
          <SidebarNavGroup
            group={analyticsGroup}
            items={analytics.visibleChildren}
            open={analytics.open}
            onToggle={() => analytics.setOpen((v) => !v)}
            active={analytics.active}
          />
          <SidebarNavGroup
            group={craftGroup}
            items={craft.visibleChildren}
            open={craft.open}
            onToggle={() => craft.setOpen((v) => !v)}
            active={craft.active}
          />

          {visibleTopLevelLinks.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              className={({ isActive }) =>
                [
                  "group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200",
                  isActive
                    ? "bg-amber-500/10 text-amber-400 ring-1 ring-amber-500/20 shadow-sm"
                    : "text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-200",
                ].join(" ")
              }
            >
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-zinc-800/80 text-xs text-inherit opacity-70 transition-opacity group-hover:opacity-100">
                {l.icon}
              </span>
              {l.label}
            </NavLink>
          ))}
        </nav>

        <div className="space-y-3 border-t border-zinc-800/80 p-4">
          <div className="rounded-xl bg-zinc-900/60 px-3 py-2.5 ring-1 ring-zinc-800/80">
            <p className="text-[0.65rem] font-medium uppercase tracking-wider text-zinc-600">Аккаунт</p>
            <p className="mt-0.5 truncate text-sm text-zinc-300">{user?.username}</p>
            {user?.role && (
              <p className="mt-0.5 text-[0.7rem] text-zinc-500">{ROLE_LABELS[user.role] ?? user.role}</p>
            )}
          </div>
          <button
            onClick={() => {
              logout();
              navigate("/login");
            }}
            className="btn-ghost w-full text-red-400 hover:border-red-900/50 hover:bg-red-950/40 hover:text-red-300"
          >
            Выйти
          </button>
        </div>
      </aside>

      <main className="flex min-w-0 flex-1 flex-col">
        <div className="sticky top-0 z-20 flex items-center gap-3 border-b border-zinc-800/80 bg-zinc-950/90 px-4 py-3 backdrop-blur-xl lg:hidden">
          <button
            type="button"
            aria-label="Меню"
            onClick={() => setMenuOpen(true)}
            className="btn-ghost !px-3 !py-1.5 text-lg leading-none"
          >
            ☰
          </button>
          <div className="flex min-w-0 items-center gap-2">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-amber-400 to-amber-600">
              <span className="text-xs font-black text-zinc-950">L4</span>
            </div>
            <span className="truncate text-sm font-semibold text-zinc-100">Lu4 Analytics</span>
          </div>
        </div>

        <div className="w-full min-w-0 flex-1 p-4 sm:p-6 lg:p-8">
          {saveError && (
            <div className="mb-4 rounded-xl border border-red-900/50 bg-red-950/40 px-4 py-3 text-sm text-red-300">
              {saveError}
            </div>
          )}
          <Suspense fallback={<LoadingState />}>
            <Outlet />
          </Suspense>
        </div>
      </main>
    </div>
  );
}
