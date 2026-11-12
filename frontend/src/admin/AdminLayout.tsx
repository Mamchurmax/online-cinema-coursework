import { NavLink, Outlet } from "react-router";

import { useAuth } from "../auth/AuthProvider";
import { StateMessage } from "../components/StateMessage";

const SECTIONS = [
  { to: "/admin/titles", label: "Тайтли" },
  { to: "/admin/videos", label: "Відео" },
  { to: "/admin/payments", label: "Платежі" },
  { to: "/admin/plans", label: "Тарифи" },
  { to: "/admin/users", label: "Користувачі" },
  { to: "/admin/ads", label: "Реклама" },
  { to: "/admin/reports", label: "Звіти" },
];

/** Admin area: only users with the `admin` role get past this (the API checks it too). */
export function AdminLayout() {
  const { user, isLoading } = useAuth();

  if (isLoading) return null;
  if (!user || user.role !== "admin") {
    return <StateMessage title="Доступ лише для адміністраторів">Увійдіть як адміністратор.</StateMessage>;
  }

  return (
    <section className="admin">
      <header className="admin__header">
        <h1 className="page-title">Адмін-панель</h1>
        <nav className="admin__nav" aria-label="Розділи адмін-панелі">
          {SECTIONS.map((section) => (
            <NavLink key={section.to} to={section.to} className="admin__tab">
              {section.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <Outlet />
    </section>
  );
}
