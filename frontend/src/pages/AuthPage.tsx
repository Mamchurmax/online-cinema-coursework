import { type FormEvent, useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router";

import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthProvider";

type Mode = "login" | "register";

/** Only local paths are allowed after login, so ?next= cannot send users to another site. */
function safeNext(next: string | null): string {
  return next && next.startsWith("/") && !next.startsWith("//") ? next : "/";
}

function errorMessage(error: unknown, mode: Mode): string {
  if (error instanceof ApiError) {
    if (mode === "login" && error.status === 401) return "Невірний email або пароль.";
    if (mode === "register" && error.status === 409) return "Цей email уже зареєстровано.";
    if (error.status === 422) return "Перевірте email і пароль (щонайменше 8 символів).";
  }
  return "Не вдалося зв'язатися з сервером. Спробуйте ще раз.";
}

export function AuthPage({ mode }: { mode: Mode }) {
  const { user, login, register } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = safeNext(params.get("next"));

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (user) return <Navigate to={next} replace />;

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (mode === "login") await login(email, password);
      else await register(email, password, displayName);
      navigate(next, { replace: true });
    } catch (err) {
      setError(errorMessage(err, mode));
    } finally {
      setSubmitting(false);
    }
  };

  const isLogin = mode === "login";
  const switchTo = `${isLogin ? "/register" : "/login"}${next !== "/" ? `?next=${encodeURIComponent(next)}` : ""}`;

  return (
    <section className="auth">
      <h1 className="page-title">{isLogin ? "Вхід" : "Реєстрація"}</h1>
      <p className="muted">
        {isLogin ? "Увійдіть, щоб дивитися фільми й серіали." : "Створіть акаунт — тариф Free діє одразу."}
      </p>

      <form className="auth__form" onSubmit={onSubmit} noValidate={false}>
        {!isLogin && (
          <label className="field">
            <span className="field__label">Ім'я</span>
            <input
              className="input"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              required
              maxLength={100}
              autoComplete="nickname"
            />
          </label>
        )}
        <label className="field">
          <span className="field__label">Email</span>
          <input
            className="input"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
        </label>
        <label className="field">
          <span className="field__label">Пароль</span>
          <input
            className="input"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={isLogin ? undefined : 8}
            autoComplete={isLogin ? "current-password" : "new-password"}
          />
        </label>

        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}

        <button className="button" type="submit" disabled={submitting}>
          {submitting ? "Зачекайте…" : isLogin ? "Увійти" : "Зареєструватися"}
        </button>
      </form>

      <p className="muted">
        {isLogin ? "Ще немає акаунта? " : "Уже є акаунт? "}
        <Link to={switchTo} className="link">
          {isLogin ? "Зареєструватися" : "Увійти"}
        </Link>
      </p>
    </section>
  );
}
