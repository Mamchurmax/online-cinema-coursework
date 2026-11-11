import { Link } from "react-router";

import type { TitleListItem } from "../api/types";
import { formatRating, TITLE_TYPE_LABEL } from "../utils/format";
import { Poster } from "./Poster";

export function TitleCard({ title }: { title: TitleListItem }) {
  const rating = formatRating(title.rating);
  const genres = title.genres.slice(0, 2).map((g) => g.name).join(", ");

  return (
    <Link to={`/titles/${title.id}`} className="title-card">
      <div className="title-card__poster">
        <Poster src={title.poster_url} title={title.title} />
        {rating && <span className="badge badge--rating">★ {rating}</span>}
        {title.type === "series" && <span className="badge badge--type">{TITLE_TYPE_LABEL.series}</span>}
      </div>
      <h3 className="title-card__name">{title.title}</h3>
      <p className="title-card__meta">
        {[title.release_year, genres].filter(Boolean).join(" · ") || " "}
      </p>
    </Link>
  );
}

export function TitleCardSkeleton() {
  return (
    <div className="title-card title-card--skeleton" aria-hidden="true">
      <div className="title-card__poster skeleton" />
      <div className="skeleton skeleton--line" />
      <div className="skeleton skeleton--line skeleton--short" />
    </div>
  );
}
