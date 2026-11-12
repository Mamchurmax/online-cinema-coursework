import { Link, Navigate } from "react-router";

import type { HistoryEntry } from "../api/types";
import { useAuth } from "../auth/AuthProvider";
import { Poster } from "../components/Poster";
import { StateMessage } from "../components/StateMessage";
import { useRemoveFromHistory, useWatchHistory } from "../hooks/useHistory";
import { formatClock } from "../utils/format";
import { historyLink, minutesLeft } from "../utils/history";

const dateFormat = new Intl.DateTimeFormat("uk-UA", {
  day: "numeric",
  month: "long",
  hour: "2-digit",
  minute: "2-digit",
});

export function HistoryPage() {
  const { user, isLoading } = useAuth();
  const history = useWatchHistory();

  if (!isLoading && !user) return <Navigate to="/login?next=%2Fhistory" replace />;

  return (
    <section>
      <h1 className="page-title">Історія переглядів</h1>

      {history.isError ? (
        <StateMessage title="Не вдалося завантажити історію" />
      ) : !history.data ? (
        <div className="history-list" aria-busy="true">
          {[0, 1, 2].map((i) => (
            <div key={i} className="history-item skeleton" style={{ height: 96 }} />
          ))}
        </div>
      ) : history.data.length === 0 ? (
        <StateMessage
          title="Ви ще нічого не дивилися"
          action={
            <Link to="/" className="button">
              До каталогу
            </Link>
          }
        >
          Тут з'являться фільми й серіали, які ви почнете дивитися.
        </StateMessage>
      ) : (
        <ul className="history-list">
          {history.data.map((entry) => (
            <HistoryItem key={entry.video_asset_id} entry={entry} />
          ))}
        </ul>
      )}
    </section>
  );
}

function HistoryItem({ entry }: { entry: HistoryEntry }) {
  const remove = useRemoveFromHistory();
  const percent = Math.min(100, (entry.progress_sec / entry.duration_sec) * 100);

  return (
    <li className="history-item">
      <Link to={historyLink(entry)} className="history-item__poster">
        <Poster src={entry.poster_url} title={entry.title} />
      </Link>
      <div className="history-item__info">
        <Link to={`/titles/${entry.title_id}`} className="history-item__title">
          {entry.title}
        </Link>
        {entry.episode && (
          <p className="muted">
            Сезон {entry.episode.season_number}, епізод {entry.episode.number}: {entry.episode.name}
          </p>
        )}
        <div className="progress progress--inline">
          <div className="progress__bar" style={{ width: `${percent}%` }} />
        </div>
        <p className="muted history-item__meta">
          {minutesLeft(entry)}
          {!entry.completed && ` · зупинились на ${formatClock(entry.progress_sec)}`} ·{" "}
          {dateFormat.format(new Date(entry.last_watched_at))}
        </p>
      </div>
      <div className="history-item__actions">
        <Link to={historyLink(entry)} className="button button--small">
          {entry.completed ? "Ще раз" : "Продовжити"}
        </Link>
        <button
          className="button button--ghost button--small"
          disabled={remove.isPending}
          onClick={() => remove.mutate(entry.video_asset_id)}
        >
          Видалити
        </button>
      </div>
    </li>
  );
}
