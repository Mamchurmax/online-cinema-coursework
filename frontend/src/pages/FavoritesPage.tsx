import { Link, Navigate } from "react-router";

import { useAuth } from "../auth/AuthProvider";
import { StateMessage } from "../components/StateMessage";
import { TitleCard, TitleCardSkeleton } from "../components/TitleCard";
import { useFavorites } from "../hooks/useAccount";

export function FavoritesPage() {
  const { user, isLoading } = useAuth();
  const favorites = useFavorites();

  if (!isLoading && !user) return <Navigate to="/login?next=%2Ffavorites" replace />;

  return (
    <section>
      <h1 className="page-title">Вибране</h1>
      {favorites.isError ? (
        <StateMessage title="Не вдалося завантажити «Вибране»" />
      ) : !favorites.data ? (
        <div className="title-grid">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <TitleCardSkeleton key={i} />
          ))}
        </div>
      ) : favorites.data.length === 0 ? (
        <StateMessage
          title="Тут поки порожньо"
          action={
            <Link to="/" className="button">
              До каталогу
            </Link>
          }
        >
          Натисніть «♡ У вибране» на сторінці фільму, щоб зберегти його тут.
        </StateMessage>
      ) : (
        <div className="title-grid">
          {favorites.data.map((title) => (
            <TitleCard key={title.id} title={title} />
          ))}
        </div>
      )}
    </section>
  );
}
