import { Link, NavLink, Outlet, useLocation } from "react-router";

import { useAuth } from "../auth/AuthProvider";
import { useMySubscription } from "../hooks/useAccount";
import { useApiHealth } from "../hooks/useApiHealth";
import { NotificationBell } from "./NotificationBell";

export function Layout() {
  const { user } = useAuth();
  return (
    <div className="app">
      <header className="header">
        <div className="container header__inner">
          <Link to="/" className="logo">
            <span className="logo__mark" aria-hidden="true">
              ▶
            </span>
            Кінотеатр
          </Link>
          <nav className="nav">
            <NavLink to="/" end className="nav__link">
              Каталог
            </NavLink>
            {user && (
              <>
                <NavLink to="/favorites" className="nav__link">
                  Вибране
                </NavLink>
                <NavLink to="/history" className="nav__link">
                  Історія
                </NavLink>
              </>
            )}
            <NavLink to="/plans" className="nav__link">
              Тарифи
            </NavLink>
          </nav>
          <UserMenu />
        </div>
      </header>

      <main className="container main">
        <Outlet />
      </main>

      <footer className="footer">
        <div className="container footer__inner">
          <span>Онлайн-кінотеатр · курсова робота</span>
          <ApiStatus />
        </div>
      </footer>
    </div>
  );
}

function UserMenu() {
  const { user, isLoading, logout } = useAuth();
  const location = useLocation();

  if (isLoading) return <div className="user-menu" aria-busy="true" />;

  if (!user) {
    const onAuthPage = ["/login", "/register"].includes(location.pathname);
    const next = onAuthPage ? "" : `?next=${encodeURIComponent(location.pathname + location.search)}`;
    return (
      <div className="user-menu">
        <Link to={`/login${next}`} className="nav__link">
          Увійти
        </Link>
        <Link to={`/register${next}`} className="button button--small">
          Реєстрація
        </Link>
      </div>
    );
  }

  return (
    <div className="user-menu">
      <NotificationBell />
      <span className="user-menu__name" title={user.email}>
        {user.display_name}
        {user.role === "admin" && <span className="user-menu__role">адмін</span>}
      </span>
      <PlanBadge />
      <button className="button button--ghost button--small" onClick={logout}>
        Вийти
      </button>
    </div>
  );
}

function ApiStatus() {
  const { isSuccess, isError } = useApiHealth();
  const state = isSuccess ? "ok" : isError ? "down" : "pending";
  const label = { ok: "API доступне", down: "API недоступне", pending: "Перевірка API…" }[state];

  return (
    <span className={`api-status api-status--${state}`} role="status">
      <span className="api-status__dot" aria-hidden="true" />
      {label}
    </span>
  );
}

function PlanBadge() {
  const { data } = useMySubscription();
  if (!data?.subscription) return null;
  return <span className="user-menu__role user-menu__role--premium">{data.plan.name}</span>;
}
