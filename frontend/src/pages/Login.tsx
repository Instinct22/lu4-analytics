import { FormEvent, useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { defaultHomePath, useAuth } from "../hooks/useAuth";

export default function Login() {
  const { user, loading, login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    document.documentElement.classList.add("dark");
  }, []);

  if (!loading && user) return <Navigate to={defaultHomePath(user.permissions)} replace />;

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await login(username, password);
    } catch {
      setError("Неверный логин или пароль");
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-surface bg-mesh-dark px-4">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_120%,rgba(245,158,11,0.12),transparent_50%)]" />

      <form onSubmit={onSubmit} className="panel relative w-full max-w-sm space-y-5 p-8 shadow-glow">
        <div className="text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-400 to-amber-600 shadow-glow">
            <span className="text-lg font-black text-zinc-950">L4</span>
          </div>
          <h1 className="text-xl font-semibold tracking-tight text-zinc-50">Lu4 Analytics</h1>
          <p className="mt-1 text-sm text-zinc-500">Войдите в панель управления</p>
        </div>

        {error && (
          <p className="rounded-xl border border-red-900/50 bg-red-950/40 px-3 py-2 text-center text-sm text-red-300">
            {error}
          </p>
        )}

        <div className="space-y-3">
          <input
            className="input"
            placeholder="Логин"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
          />
          <input
            className="input"
            type="password"
            placeholder="Пароль"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </div>

        <button type="submit" className="btn-primary w-full py-2.5">
          Войти
        </button>
      </form>
    </div>
  );
}
