import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";

import type { TitleDetail } from "../api/types";
import { useCountries, useGenres, useTitle } from "../hooks/useCatalog";
import { formatClock } from "../utils/format";
import { adminApi, errorText, type TitleInput } from "./api";

const EMPTY: TitleInput = {
  type: "movie",
  title: "",
  description: "",
  release_year: null,
  rating: null,
  poster_url: null,
  backdrop_url: null,
  duration: null,
  genre_ids: [],
  country_codes: [],
};

function toInput(title: TitleDetail): TitleInput {
  return {
    type: title.type,
    title: title.title,
    description: title.description,
    release_year: title.release_year,
    rating: title.rating,
    poster_url: title.poster_url,
    backdrop_url: title.backdrop_url,
    duration: title.duration,
    genre_ids: title.genres.map((g) => g.id),
    country_codes: title.countries.map((c) => c.code),
  };
}

const numberOrNull = (value: string) => (value === "" ? null : Number(value));

export function AdminTitleEditPage() {
  const params = useParams();
  const isNew = params.titleId === "new";
  const titleId = isNew ? NaN : Number(params.titleId);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const existing = useTitle(titleId);
  const genres = useGenres();
  const countries = useCountries();
  const [form, setForm] = useState<TitleInput>(EMPTY);

  useEffect(() => {
    if (existing.data) setForm(toInput(existing.data));
  }, [existing.data]);

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["title", titleId] });
    queryClient.invalidateQueries({ queryKey: ["admin"] });
    queryClient.invalidateQueries({ queryKey: ["titles"] });
  };

  const save = useMutation({
    mutationFn: () => (isNew ? adminApi.createTitle(form) : adminApi.updateTitle(titleId, form)),
    onSuccess: (title) => {
      refresh();
      if (isNew) navigate(`/admin/titles/${title.id}`, { replace: true });
    },
  });

  const set = <K extends keyof TitleInput>(key: K, value: TitleInput[K]) => setForm((f) => ({ ...f, [key]: value }));
  const toggle = <K extends "genre_ids" | "country_codes">(key: K, value: TitleInput[K][number]) =>
    setForm((f) => {
      const list = f[key] as (typeof value)[];
      return { ...f, [key]: list.includes(value) ? list.filter((v) => v !== value) : [...list, value] };
    });

  if (!isNew && existing.isPending) return <div className="skeleton" style={{ height: 400 }} />;

  return (
    <div className="admin__section">
      <Link to="/admin/titles" className="back-link">
        ← Усі тайтли
      </Link>
      <h2 className="section-title section-title--compact">{isNew ? "Новий тайтл" : form.title}</h2>

      <form
        className="admin-form"
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          save.mutate();
        }}
      >
        <label className="field">
          <span className="field__label">Тип</span>
          <select className="input" value={form.type} onChange={(e) => set("type", e.target.value as TitleInput["type"])}>
            <option value="movie">Фільм</option>
            <option value="series">Серіал</option>
          </select>
        </label>
        <label className="field admin-form__wide">
          <span className="field__label">Назва</span>
          <input className="input" value={form.title} onChange={(e) => set("title", e.target.value)} required maxLength={255} />
        </label>
        <label className="field admin-form__full">
          <span className="field__label">Опис</span>
          <textarea
            className="input"
            rows={4}
            value={form.description}
            onChange={(e) => set("description", e.target.value)}
          />
        </label>
        <label className="field">
          <span className="field__label">Рік</span>
          <input className="input" type="number" min={1870} max={2100} value={form.release_year ?? ""}
                 onChange={(e) => set("release_year", numberOrNull(e.target.value))} />
        </label>
        <label className="field">
          <span className="field__label">Рейтинг (0–10)</span>
          <input className="input" type="number" min={0} max={10} step={0.1} value={form.rating ?? ""}
                 onChange={(e) => set("rating", e.target.value === "" ? null : e.target.value)} />
        </label>
        <label className="field">
          <span className="field__label">Тривалість, хв</span>
          <input className="input" type="number" min={1} value={form.duration ?? ""}
                 onChange={(e) => set("duration", numberOrNull(e.target.value))} />
        </label>
        <label className="field admin-form__wide">
          <span className="field__label">Постер (URL)</span>
          <input className="input" type="url" value={form.poster_url ?? ""} onChange={(e) => set("poster_url", e.target.value || null)} />
        </label>
        <label className="field admin-form__wide">
          <span className="field__label">Фон (URL)</span>
          <input className="input" type="url" value={form.backdrop_url ?? ""}
                 onChange={(e) => set("backdrop_url", e.target.value || null)} />
        </label>

        <fieldset className="admin-form__full admin-form__choices">
          <legend className="field__label">Жанри</legend>
          {genres.data?.map((genre) => (
            <label key={genre.id} className={`chip ${form.genre_ids.includes(genre.id) ? "chip--active" : ""}`}>
              <input type="checkbox" hidden checked={form.genre_ids.includes(genre.id)} onChange={() => toggle("genre_ids", genre.id)} />
              {genre.name}
            </label>
          ))}
        </fieldset>
        <fieldset className="admin-form__full admin-form__choices">
          <legend className="field__label">Країни</legend>
          {countries.data?.map((country) => (
            <label key={country.code} className={`chip ${form.country_codes.includes(country.code) ? "chip--active" : ""}`}>
              <input type="checkbox" hidden checked={form.country_codes.includes(country.code)}
                     onChange={() => toggle("country_codes", country.code)} />
              {country.name}
            </label>
          ))}
        </fieldset>

        <div className="admin-form__full admin-form__actions">
          <button className="button" disabled={save.isPending}>
            {save.isPending ? "Збереження…" : isNew ? "Створити" : "Зберегти"}
          </button>
          {save.isSuccess && !isNew && <span className="muted">Збережено ✓</span>}
          {save.isError && <span className="form-error">{errorText(save.error)}</span>}
        </div>
      </form>

      {existing.data && existing.data.type === "movie" && <MovieVideo title={existing.data} onChange={refresh} />}
      {existing.data && existing.data.type === "series" && <SeasonsEditor title={existing.data} onChange={refresh} />}
    </div>
  );
}

function useStreams() {
  return useQuery({ queryKey: ["admin", "streams"], queryFn: adminApi.streams });
}

function StreamSelect({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const streams = useStreams();
  return (
    <select className="input" value={value} onChange={(e) => onChange(e.target.value)} required>
      <option value="">Оберіть HLS-папку…</option>
      {streams.data
        ?.filter((s) => !s.directory.startsWith("ads/"))
        .map((s) => (
          <option key={s.directory} value={s.directory}>
            {s.directory} · {s.qualities.join("/")} · {formatClock(s.duration_sec)}
          </option>
        ))}
    </select>
  );
}

function MovieVideo({ title, onChange }: { title: TitleDetail; onChange: () => void }) {
  const [stream, setStream] = useState("");
  const attach = useMutation({ mutationFn: () => adminApi.attachTitleVideo(title.id, stream), onSuccess: onChange });

  return (
    <section className="admin-card">
      <h3>Відео</h3>
      <p className="muted">
        {title.has_video ? "Відео прив'язано. Можна замінити на інше:" : "Відео ще немає. Оберіть перекодовану папку з media/hls:"}
      </p>
      <form className="admin__inline-form" onSubmit={(e) => { e.preventDefault(); attach.mutate(); }}>
        <StreamSelect value={stream} onChange={setStream} />
        <button className="button" disabled={attach.isPending}>Прив'язати</button>
        {attach.isError && <span className="form-error">{errorText(attach.error)}</span>}
      </form>
    </section>
  );
}

function SeasonsEditor({ title, onChange }: { title: TitleDetail; onChange: () => void }) {
  const nextSeason = Math.max(0, ...title.seasons.map((s) => s.number)) + 1;
  const addSeason = useMutation({
    mutationFn: () => adminApi.addSeason(title.id, nextSeason, `Сезон ${nextSeason}`),
    onSuccess: onChange,
  });
  const deleteSeason = useMutation({ mutationFn: adminApi.deleteSeason, onSuccess: onChange });
  const deleteEpisode = useMutation({ mutationFn: adminApi.deleteEpisode, onSuccess: onChange });

  return (
    <section className="admin-card">
      <div className="admin__toolbar">
        <h3>Сезони та епізоди</h3>
        <button className="button button--small" onClick={() => addSeason.mutate()} disabled={addSeason.isPending}>
          + Сезон {nextSeason}
        </button>
      </div>
      {title.seasons.length === 0 && <p className="muted">Сезонів ще немає.</p>}
      {title.seasons.map((season) => (
        <details key={season.id} className="admin-season">
          <summary>
            {season.name} · {season.episodes.length} епізодів
            <button
              className="button button--ghost button--small"
              onClick={(e) => {
                e.preventDefault();
                if (confirm(`Видалити «${season.name}» з усіма епізодами?`)) deleteSeason.mutate(season.id);
              }}
            >
              Видалити сезон
            </button>
          </summary>
          <ul className="admin-episodes">
            {season.episodes.map((episode) => (
              <EpisodeRow
                key={episode.id}
                id={episode.id}
                label={`${episode.number}. ${episode.name}`}
                hasVideo={episode.has_video}
                onChange={onChange}
                onDelete={() => deleteEpisode.mutate(episode.id)}
              />
            ))}
          </ul>
          <AddEpisodeForm seasonId={season.id} next={Math.max(0, ...season.episodes.map((e) => e.number)) + 1} onAdded={onChange} />
        </details>
      ))}
    </section>
  );
}

function EpisodeRow(props: { id: number; label: string; hasVideo: boolean; onChange: () => void; onDelete: () => void }) {
  const [stream, setStream] = useState("");
  const attach = useMutation({ mutationFn: () => adminApi.attachEpisodeVideo(props.id, stream), onSuccess: props.onChange });
  return (
    <li className="admin-episode">
      <span>
        {props.label} {props.hasVideo && <span className="status status--succeeded">відео</span>}
      </span>
      <form className="admin__inline-form" onSubmit={(e) => { e.preventDefault(); attach.mutate(); }}>
        <StreamSelect value={stream} onChange={setStream} />
        <button className="button button--ghost button--small" disabled={!stream || attach.isPending}>
          Прив'язати відео
        </button>
        <button type="button" className="button button--ghost button--small" onClick={props.onDelete}>
          ✕
        </button>
      </form>
    </li>
  );
}

function AddEpisodeForm({ seasonId, next, onAdded }: { seasonId: number; next: number; onAdded: () => void }) {
  const [name, setName] = useState("");
  const add = useMutation({
    mutationFn: () => adminApi.addEpisode(seasonId, { number: next, name, description: "", duration: null }),
    onSuccess: () => {
      setName("");
      onAdded();
    },
  });
  return (
    <form className="admin__inline-form" onSubmit={(e) => { e.preventDefault(); add.mutate(); }}>
      <input className="input" placeholder={`Епізод ${next}: назва`} value={name} onChange={(e) => setName(e.target.value)} required />
      <button className="button button--small" disabled={add.isPending}>+ Епізод</button>
      {add.isError && <span className="form-error">{errorText(add.error)}</span>}
    </form>
  );
}
