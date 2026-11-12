import { useEffect, useRef, useState } from "react";

import { useMarkNotificationsRead, useNotifications } from "../hooks/useAccount";

const timeFormat = new Intl.DateTimeFormat("uk-UA", {
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});

const ICONS = {
  payment_succeeded: "✓",
  payment_failed: "✕",
  subscription_activated: "★",
  subscription_expiring: "⏰",
} as const;

export function NotificationBell() {
  const { data } = useNotifications();
  const markRead = useMarkNotificationsRead();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const unread = data?.unread_count ?? 0;

  // Close on a click outside or Escape.
  useEffect(() => {
    if (!open) return;
    const onClick = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const toggle = () => {
    const opening = !open;
    setOpen(opening);
    if (opening && unread > 0) markRead.mutate(); // seen = read
  };

  return (
    <div className="bell" ref={rootRef}>
      <button
        className="bell__button"
        onClick={toggle}
        aria-expanded={open}
        aria-label={unread ? `Сповіщення: ${unread} непрочитаних` : "Сповіщення"}
      >
        🔔
        {unread > 0 && <span className="bell__count">{unread > 9 ? "9+" : unread}</span>}
      </button>

      {open && (
        <div className="bell__panel" role="dialog" aria-label="Сповіщення">
          <h2 className="bell__title">Сповіщення</h2>
          {!data?.items.length ? (
            <p className="muted bell__empty">Поки що сповіщень немає.</p>
          ) : (
            <ul className="bell__list">
              {data.items.map((item) => (
                <li key={item.id} className={`bell__item ${item.is_read ? "" : "bell__item--unread"}`}>
                  <span className={`bell__icon bell__icon--${item.type}`} aria-hidden="true">
                    {ICONS[item.type]}
                  </span>
                  <div>
                    <p className="bell__message">{item.message}</p>
                    <time className="muted bell__time" dateTime={item.created_at}>
                      {timeFormat.format(new Date(item.created_at))}
                    </time>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
