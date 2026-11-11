import type { ReactNode } from "react";

interface StateMessageProps {
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}

/** Centered message for empty results and errors. */
export function StateMessage({ title, children, action }: StateMessageProps) {
  return (
    <div className="state-message">
      <h2 className="state-message__title">{title}</h2>
      {children && <p className="muted">{children}</p>}
      {action}
    </div>
  );
}
