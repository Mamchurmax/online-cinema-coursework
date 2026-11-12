import { useNavigate } from "react-router";

import { useAuth } from "../auth/AuthProvider";
import { useFavoriteIds, useToggleFavorite } from "../hooks/useAccount";

/** Heart toggle; guests are sent to sign in first. */
export function FavoriteButton({ titleId }: { titleId: number }) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const ids = useFavoriteIds();
  const toggle = useToggleFavorite();
  const active = ids.data?.has(titleId) ?? false;

  const onClick = () => {
    if (!user) {
      navigate(`/login?next=${encodeURIComponent(`/titles/${titleId}`)}`);
      return;
    }
    toggle.mutate({ titleId, add: !active });
  };

  return (
    <button
      className={`button button--ghost favorite-button ${active ? "favorite-button--active" : ""}`}
      aria-pressed={active}
      disabled={toggle.isPending}
      onClick={onClick}
    >
      {active ? "♥ У вибраному" : "♡ У вибране"}
    </button>
  );
}
