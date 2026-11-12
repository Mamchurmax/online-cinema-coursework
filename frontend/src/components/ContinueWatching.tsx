import { Link } from "react-router";

import type { HistoryEntry } from "../api/types";
import { useContinueWatching } from "../hooks/useHistory";
import { historyLink, minutesLeft } from "../utils/history";
import { Poster } from "./Poster";

/** "Continue watching" row above the catalog; hidden for guests and empty histories. */
export function ContinueWatching() {
  const { data } = useContinueWatching();
  if (!data?.length) return null;

  return (
    <section className="continue" aria-label="Продовжити перегляд">
      <h2 className="section-title section-title--compact">Продовжити перегляд</h2>
      <div className="continue__row">
        {data.map((entry) => (
          <ContinueCard key={entry.video_asset_id} entry={entry} />
        ))}
      </div>
    </section>
  );
}

function ContinueCard({ entry }: { entry: HistoryEntry }) {
  const percent = Math.min(100, (entry.progress_sec / entry.duration_sec) * 100);

  return (
    <Link to={historyLink(entry)} className="continue-card">
      <div className="continue-card__image">
        <Poster src={entry.backdrop_url ?? entry.poster_url} title={entry.title} />
        <span className="continue-card__play" aria-hidden="true">
          ▶
        </span>
        <div className="progress" aria-label={`Переглянуто ${Math.round(percent)}%`}>
          <div className="progress__bar" style={{ width: `${percent}%` }} />
        </div>
      </div>
      <h3 className="continue-card__title">{entry.title}</h3>
      <p className="continue-card__meta">
        {entry.episode && `С${entry.episode.season_number} Е${entry.episode.number} · `}
        {minutesLeft(entry)}
      </p>
    </Link>
  );
}
