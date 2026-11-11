import { useEffect, useState } from "react";

import type { CatalogFilters, CatalogSort, SortOrder, TitleType } from "../../api/types";
import { useCountries, useGenres } from "../../hooks/useCatalog";
import { hasActiveFilters, SORT_OPTIONS } from "./filters";

interface FilterBarProps {
  filters: CatalogFilters;
  onChange: (patch: Partial<CatalogFilters>) => void;
  onReset: () => void;
}

const TYPE_OPTIONS: { value: TitleType | undefined; label: string }[] = [
  { value: undefined, label: "Усі" },
  { value: "movie", label: "Фільми" },
  { value: "series", label: "Серіали" },
];

const SEARCH_DELAY_MS = 400;
const MIN_YEAR = 1870;
const MAX_YEAR = 2100;

export function FilterBar({ filters, onChange, onReset }: FilterBarProps) {
  const genres = useGenres();
  const countries = useCountries();

  // The input updates instantly; the URL (and the request) only after a pause in typing.
  const [query, setQuery] = useState(filters.q ?? "");
  useEffect(() => setQuery(filters.q ?? ""), [filters.q]);
  useEffect(() => {
    if (query.trim() === (filters.q ?? "")) return;
    const timer = setTimeout(() => onChange({ q: query.trim() || undefined }), SEARCH_DELAY_MS);
    return () => clearTimeout(timer);
  }, [query, filters.q, onChange]);

  const selectedGenres = new Set(filters.genre ?? []);
  const toggleGenre = (id: number) => {
    const next = new Set(selectedGenres);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    onChange({ genre: [...next] });
  };

  return (
    <section className="filters" aria-label="Пошук і фільтри">
      <div className="filters__row">
        <input
          type="search"
          className="input filters__search"
          placeholder="Пошук за назвою…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          aria-label="Пошук за назвою"
        />

        <div className="segmented" role="group" aria-label="Тип">
          {TYPE_OPTIONS.map((option) => (
            <button
              key={option.label}
              className={`segmented__item ${filters.type === option.value ? "segmented__item--active" : ""}`}
              aria-pressed={filters.type === option.value}
              onClick={() => onChange({ type: option.value })}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      <div className="filters__row">
        <label className="field">
          <span className="field__label">Країна</span>
          <select
            className="input"
            value={filters.country?.[0] ?? ""}
            onChange={(event) => onChange({ country: event.target.value ? [event.target.value] : [] })}
          >
            <option value="">Будь-яка</option>
            {countries.data?.map((country) => (
              <option key={country.code} value={country.code}>
                {country.name}
              </option>
            ))}
          </select>
        </label>

        <YearField
          label="Рік від"
          placeholder="1900"
          value={filters.year_from}
          onCommit={(year_from) => onChange({ year_from })}
        />
        <YearField
          label="Рік до"
          placeholder="2026"
          value={filters.year_to}
          onCommit={(year_to) => onChange({ year_to })}
        />

        <label className="field">
          <span className="field__label">Сортування</span>
          <select
            className="input"
            value={`${filters.sort}:${filters.order}`}
            onChange={(event) => {
              const [sort, order] = event.target.value.split(":") as [CatalogSort, SortOrder];
              onChange({ sort, order });
            }}
          >
            {SORT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        {hasActiveFilters(filters) && (
          <button className="button button--ghost filters__reset" onClick={onReset}>
            Скинути фільтри
          </button>
        )}
      </div>

      {genres.data && genres.data.length > 0 && (
        <div className="chips" role="group" aria-label="Жанри">
          {genres.data.map((genre) => (
            <button
              key={genre.id}
              className={`chip ${selectedGenres.has(genre.id) ? "chip--active" : ""}`}
              aria-pressed={selectedGenres.has(genre.id)}
              onClick={() => toggleGenre(genre.id)}
            >
              {genre.name}
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

interface YearFieldProps {
  label: string;
  placeholder: string;
  value: number | undefined;
  onCommit: (year: number | undefined) => void;
}

/** Applies the year on Enter or blur, not on every keystroke ("1", "19", "199"...). */
function YearField({ label, placeholder, value, onCommit }: YearFieldProps) {
  const [text, setText] = useState(value?.toString() ?? "");
  useEffect(() => setText(value?.toString() ?? ""), [value]);

  const commit = () => {
    const trimmed = text.trim();
    if (trimmed === "") {
      if (value !== undefined) onCommit(undefined);
      return;
    }
    const year = Number(trimmed);
    if (Number.isInteger(year) && year >= MIN_YEAR && year <= MAX_YEAR) {
      if (year !== value) onCommit(year);
    } else {
      setText(value?.toString() ?? ""); // invalid input: restore the applied value
    }
  };

  return (
    <label className="field field--narrow">
      <span className="field__label">{label}</span>
      <input
        type="number"
        className="input"
        min={MIN_YEAR}
        max={MAX_YEAR}
        placeholder={placeholder}
        value={text}
        onChange={(event) => setText(event.target.value)}
        onBlur={commit}
        onKeyDown={(event) => event.key === "Enter" && commit()}
      />
    </label>
  );
}
