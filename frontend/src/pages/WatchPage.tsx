import { useQuery } from "@tanstack/react-query";
import { Link, Navigate, useLocation, useParams } from "react-router";

import { ApiError } from "../api/client";
import { playbackApi } from "../api/playback";
import { useAuth } from "../auth/AuthProvider";
import { VideoPlayer } from "../components/player/VideoPlayer";
import { StateMessage } from "../components/StateMessage";
import { useTitle } from "../hooks/useCatalog";

export function WatchPage() {
  const titleId = Number(useParams().titleId);
  const { user, isLoading: authLoading } = useAuth();
  const location = useLocation();
  const title = useTitle(titleId);

  const playback = useQuery({
    queryKey: ["playback", "title", titleId, user?.id],
    queryFn: ({ signal }) => playbackApi.startTitle(titleId, signal),
    enabled: Boolean(user) && Number.isInteger(titleId),
    staleTime: 0,
    gcTime: 0, // a new session (and possibly a new ad) every time the page opens
  });

  if (!authLoading && !user) {
    const next = encodeURIComponent(location.pathname);
    return <Navigate to={`/login?next=${next}`} replace />;
  }

  const back = (
    <Link to={`/titles/${titleId}`} className="back-link">
      ← До сторінки фільму
    </Link>
  );

  if (playback.isError) {
    const status = playback.error instanceof ApiError ? playback.error.status : 0;
    return (
      <StateMessage
        title={status === 404 ? "Відео поки недоступне" : "Не вдалося почати перегляд"}
        action={back}
      >
        {status === 404
          ? "Для цього тайтлу ще не завантажили відео."
          : status === 403
            ? "Ваш тариф не дозволяє переглядати це відео."
            : "Спробуйте оновити сторінку."}
      </StateMessage>
    );
  }

  return (
    <section className="watch">
      <div className="watch__header">
        {back}
        <h1 className="watch__title">{title.data?.title ?? " "}</h1>
      </div>
      {playback.data ? (
        <VideoPlayer
          key={playback.data.asset_id}
          info={playback.data}
          title={title.data?.title ?? ""}
          poster={title.data?.backdrop_url}
        />
      ) : (
        <div className="player">
          <div className="player__stage skeleton" aria-busy="true" />
        </div>
      )}
    </section>
  );
}
