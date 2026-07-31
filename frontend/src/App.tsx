import { lazy } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider, defaultHomePath, useAuth } from "./hooks/useAuth";
import { PreferencesProvider } from "./hooks/usePreferences";
import MainLayout from "./layouts/MainLayout";
import Login from "./pages/Login";

// Pages load on demand so the login screen does not ship recharts and
// react-markdown. MainLayout renders the Suspense fallback.
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Charts = lazy(() => import("./pages/Charts"));
const WikiArticle = lazy(() => import("./pages/WikiArticle"));
const Statistics = lazy(() => import("./pages/Statistics"));
const SearchPage = lazy(() => import("./pages/Search"));
const CraftPage = lazy(() => import("./pages/Craft"));
const CraftBulkPage = lazy(() => import("./pages/CraftBulk"));
const WeaponUpgradesPage = lazy(() => import("./pages/WeaponUpgrades"));
const ItemsPage = lazy(() => import("./pages/Items"));
const ResourcesPage = lazy(() => import("./pages/Resources"));
const CharacterPage = lazy(() => import("./pages/Character"));
const AdminPage = lazy(() => import("./pages/Admin"));
const RaidBossesPage = lazy(() => import("./pages/RaidBosses"));

const queryClient = new QueryClient();

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="flex min-h-screen items-center justify-center bg-surface text-zinc-500">Загрузка...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function RequirePermission({
  permission,
  children,
}: {
  permission: string;
  children: React.ReactNode;
}) {
  const { user, hasPermission } = useAuth();
  if (!hasPermission(permission)) {
    return <Navigate to={defaultHomePath(user?.permissions)} replace />;
  }
  return <>{children}</>;
}

function HomeRedirect() {
  const { user } = useAuth();
  if (user?.permissions?.includes("nav.dashboard")) return <Dashboard />;
  return <Navigate to={defaultHomePath(user?.permissions)} replace />;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route
              element={
                <ProtectedRoute>
                  <PreferencesProvider>
                    <MainLayout />
                  </PreferencesProvider>
                </ProtectedRoute>
              }
            >
              <Route path="/" element={<HomeRedirect />} />
              <Route
                path="/charts"
                element={
                  <RequirePermission permission="nav.charts">
                    <Charts />
                  </RequirePermission>
                }
              />
              <Route path="/wiki/:type/:id" element={<WikiArticle />} />
              <Route
                path="/statistics"
                element={
                  <RequirePermission permission="nav.statistics">
                    <Statistics />
                  </RequirePermission>
                }
              />
              <Route
                path="/search"
                element={
                  <RequirePermission permission="nav.search">
                    <SearchPage />
                  </RequirePermission>
                }
              />
              <Route path="/craft/warehouse" element={<Navigate to="/craft/bulk" replace />} />
              <Route
                path="/craft/bulk"
                element={
                  <RequirePermission permission="nav.craft">
                    <CraftBulkPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/craft/upgrades"
                element={
                  <RequirePermission permission="nav.craft">
                    <WeaponUpgradesPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/craft"
                element={
                  <RequirePermission permission="nav.craft">
                    <CraftPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/items"
                element={
                  <RequirePermission permission="nav.items">
                    <ItemsPage />
                  </RequirePermission>
                }
              />
              <Route path="/duals" element={<Navigate to="/items" replace />} />
              <Route
                path="/resources"
                element={
                  <RequirePermission permission="nav.resources">
                    <ResourcesPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/character"
                element={
                  <RequirePermission permission="nav.character">
                    <CharacterPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/raid-bosses"
                element={
                  <RequirePermission permission="nav.raid_bosses">
                    <RaidBossesPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/admin"
                element={
                  <RequirePermission permission="nav.admin">
                    <AdminPage />
                  </RequirePermission>
                }
              />
              <Route path="/catalog/*" element={<Navigate to="/" replace />} />
              <Route path="/wiki" element={<Navigate to="/search" replace />} />
              <Route path="/analytics/*" element={<Navigate to="/craft" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}
