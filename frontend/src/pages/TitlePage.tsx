import { useState } from "react";
import { Link, useParams } from "react-router";

import { ApiError } from "../api/client";
import type { Season, TitleDetail } from "../api/types";
import { Poster } from "../components/Poster";
import { StateMessage } from "../components/StateMessage";
import { useTitle } from "../hooks/useCatalog";
import { formatDuration, formatRating, plural, TITLE_TYPE_LABEL } from "../utils/format";

export function TitlePage() {
  const titleId = Number(useParams().titleId);
  const { data: title, isPending, isError, error, refetch } = useTitle(titleId);

  const notFound = !Number.isInteger(titleId) || (error instanceof ApiError && error.status === 404);
  if (notFound) {
    return (
      <StateMessage
        title="Тайтл не знайдено"
        action={
          <Link to="/" className="button">
            До каталогу
          </Link>
        }
      >
        Можливо, його видалили або посилання неправильне.
      </StateMessage>
    );
  }

  if (isError) {
    return (
      <StateMessage
        title="Не вдалося завантажити сторінку"
        action={
          <button className="button" onClick={() => refetch()}>
            Спробувати ще раз
          </button>
        }
      />
    );
  }

  if (isPending) {
    return <TitleSkeleton />;
  }

  return (
    <article className="title-page">
      <TitleHero title={title} />
      {title.type === "series" && <Seasons seasons={title.seasons} />}
    </article>
  );
}

function TitleHero({ title }: { title: TitleDetail }) {
  const rating = formatRating(title.rating);
  const duration = formatDuration(title.duration);
  const episodes = title.seasons.reduce((sum, season) => sum + season.episodes.length, 0);

  const facts = [
    TITLE_TYPE_LABEL[title.type],
    title.release_year,
    title.type === "series" && title.seasons.length
      ? `${title.seasons.length} ${plural(title.seasons.length, ["сезон", "сезони", "сезонів"])}, ` +
        `${episodes} ${plural(episodes, ["епізод", "епізоди", "епізодів"])}`
      : null,
    duration && (title.type === "series" ? `~${duration} / епізод` : duration),
  ].filter(Boolean);

  return (
    <header
      className="title-hero"
      style={title.backdrop_url ? { backgroundImage: `url(${title.backdrop_url})` } : undefined}
    >
      <div className="title-hero__overlay">
        <Poster src={title.poster_url} title={title.title} className="title-hero__poster" />

        <div className="title-hero__info">
          <Link to="/" className="back-link">
            ← Каталог
          </Link>
          <h1 className="title-hero__name">{title.title}</h1>

          <p className="title-hero__facts">
            {rating && <span className="badge badge--rating badge--inline">★ {rating}</span>}
            {facts.join(" · ")}
          </p>

          {title.genres.length > 0 && (
            <ul className="tag-list" aria-label="Жанри">
              {title.genres.map((genre) => (
                <li key={genre.id}>
                  <Link to={`/?genre=${genre.id}`} className="chip">
                    {genre.name}
                  </Link>
                </li>
              ))}
            </ul>
          )}

          <p className="title-hero__description">{title.description || "Опис відсутній."}</p>

          {title.has_video ? (
            <Link to={`/watch/${title.id}`} className="button button--play">
              ▶ Дивитися
            </Link>
          ) : (
            <p className="muted">Онлайн-перегляд цього тайтлу поки недоступний.</p>
          )}

          {title.countries.length > 0 && (
            <p className="muted">
              {plural(title.countries.length, ["Країна", "Країни", "Країни"])}:{" "}
              {title.countries.map((country) => country.name).join(", ")}
            </p>
          )}
        </div>
      </div>
    </header>
  );
}

function Seasons({ seasons }: { seasons: Season[] }) {
  const [activeNumber, setActiveNumber] = useState(seasons[0]?.number);
  const active = seasons.find((season) => season.number === activeNumber) ?? seasons[0];

  if (!active) {
    return <p className="muted">Інформації про сезони поки немає.</p>;
  }

  return (
    <section className="seasons" aria-label="Сезони">
      <h2 className="section-title">Сезони та епізоди</h2>

      <div className="tabs" role="tablist">
        {seasons.map((season) => (
          <button
            key={season.id}
            role="tab"
            aria-selected={season.number === active.number}
            className={`tabs__item ${season.number === active.number ? "tabs__item--active" : ""}`}
            onClick={() => setActiveNumber(season.number)}
          >
            {season.name}
          </button>
        ))}
      </div>

      <ol className="episode-list" role="tabpanel">
        {active.episodes.map((episode) => (
          <li key={episode.id} className="episode">
            <span className="episode__number">{episode.number}</span>
            <div>
              <h3 className="episode__name">
                {episode.name}
                {episode.duration && <span className="muted"> · {formatDuration(episode.duration)}</span>}
              </h3>
              {episode.description && <p className="episode__description muted">{episode.description}</p>}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

function TitleSkeleton() {
  return (
    <div className="title-hero" aria-busy="true">
      <div className="title-hero__overlay">
        <div className="title-hero__poster skeleton" />
        <div className="title-hero__info">
          <div className="skeleton skeleton--heading" />
          <div className="skeleton skeleton--line skeleton--short" />
          <div className="skeleton skeleton--line" />
          <div className="skeleton skeleton--line" />
        </div>
      </div>
    </div>
  );
}
