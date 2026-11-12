import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router";

import { catalogApi } from "../api/catalog";
import type { TitleType } from "../api/types";
import { Pagination } from "../components/Pagination";
import { formatRating, TITLE_TYPE_LABEL } from "../utils/format";
import { adminApi, errorText } from "./api";

export function AdminTitlesPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);

  // Listing reuses the public catalog API (CatalogQueryBuilder on the backend).
  const titles = useQuery({
    queryKey: ["admin", "titles", query, page],
    queryFn: ({ signal }) =>
      catalogApi.searchTitles({ q: query || undefined, page, page_size: 20, sort: "added", order: "desc" }, signal),
  });

  const remove = useMutation({
    mutationFn: adminApi.deleteTitle,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "titles"] }),
  });

  const [tmdbId, setTmdbId] = useState("");
  const [tmdbType, setTmdbType] = useState<TitleType>("movie");
  const importTitle = useMutation({
    mutationFn: () => adminApi.importTitle(Number(tmdbId), tmdbType),
    onSuccess: (title) => navigate(`/admin/titles/${title.id}`),
  });

  return (
    <div className="admin__section">
      <div className="admin__toolbar">
        <input
          className="input admin__search"
          type="search"
          placeholder="Пошук за назвою…"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setPage(1);
          }}
        />
        <Link to="/admin/titles/new" className="button">
          + Додати тайтл
        </Link>
      </div>

      <form
        className="admin__inline-form"
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          importTitle.mutate();
        }}
      >
        <span className="field__label">Імпорт з TMDB:</span>
        <input
          className="input admin__narrow"
          type="number"
          min={1}
          placeholder="TMDB id"
          value={tmdbId}
          onChange={(e) => setTmdbId(e.target.value)}
          required
        />
        <select className="input admin__narrow" value={tmdbType} onChange={(e) => setTmdbType(e.target.value as TitleType)}>
          <option value="movie">Фільм</option>
          <option value="series">Серіал</option>
        </select>
        <button className="button button--ghost" disabled={importTitle.isPending}>
          {importTitle.isPending ? "Імпорт…" : "Імпортувати"}
        </button>
        {importTitle.isError && <span className="form-error">{errorText(importTitle.error)}</span>}
      </form>

      <table className="table">
        <thead>
          <tr>
            <th>Назва</th>
            <th>Тип</th>
            <th>Рік</th>
            <th>Рейтинг</th>
            <th>Відео</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {titles.data?.items.map((title) => (
            <tr key={title.id}>
              <td>
                <Link to={`/admin/titles/${title.id}`} className="link">
                  {title.title}
                </Link>
              </td>
              <td>{TITLE_TYPE_LABEL[title.type]}</td>
              <td>{title.release_year ?? "—"}</td>
              <td>{formatRating(title.rating) ?? "—"}</td>
              <td>{title.has_video ? "▶ є" : "—"}</td>
              <td className="table__actions">
                <Link to={`/titles/${title.id}`} className="link">
                  На сайті
                </Link>
                <button
                  className="button button--ghost button--small"
                  disabled={remove.isPending}
                  onClick={() => {
                    if (confirm(`Видалити «${title.title}» разом із сезонами, відео та історією переглядів?`)) {
                      remove.mutate(title.id);
                    }
                  }}
                >
                  Видалити
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {titles.data && <Pagination page={titles.data.page} pages={titles.data.pages} onChange={setPage} />}
    </div>
  );
}
