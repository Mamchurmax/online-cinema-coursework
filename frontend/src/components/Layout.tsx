import { Link, NavLink, Outlet } from "react-router";

import { useApiHealth } from "../hooks/useApiHealth";

export function Layout() {
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
          </nav>
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
