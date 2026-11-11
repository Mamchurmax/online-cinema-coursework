import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router";

import type { CatalogFilters } from "../api/types";
import { Pagination } from "../components/Pagination";
import { StateMessage } from "../components/StateMessage";
import { TitleCard, TitleCardSkeleton } from "../components/TitleCard";
import { useTitles } from "../hooks/useCatalog";
import { plural } from "../utils/format";
import { FilterBar } from "./catalog/FilterBar";
import { filtersFromParams, filtersToParams, hasActiveFilters, PAGE_SIZE } from "./catalog/filters";

export function CatalogPage() {
  const [params, setParams] = useSearchParams();
  const filters = useMemo(() => filtersFromParams(params), [params]);
  const { data, isPending, isError, isPlaceholderData, refetch } = useTitles(filters);

  const updateFilters = useCallback(
    (patch: Partial<CatalogFilters>) => {
      // Any filter change starts from the first page.
      setParams(filtersToParams({ ...filtersFromParams(params), page: 1, ...patch }));
    },
    [params, setParams],
  );

  const changePage = (page: number) => {
    updateFilters({ page });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <section>
      <div className="page-header">
        <h1 className="page-title">Каталог</h1>
        {data && (
          <span className="muted">
            {data.total} {plural(data.total, ["тайтл", "тайтли", "тайтлів"])}
          </span>
        )}
      </div>

      <FilterBar filters={filters} onChange={updateFilters} onReset={() => setParams({})} />

      {isError ? (
        <StateMessage
          title="Не вдалося завантажити каталог"
          action={
            <button className="button" onClick={() => refetch()}>
              Спробувати ще раз
            </button>
          }
        >
          Перевірте з'єднання з сервером.
        </StateMessage>
      ) : isPending ? (
        <div className="title-grid">
          {Array.from({ length: PAGE_SIZE }, (_, i) => (
            <TitleCardSkeleton key={i} />
          ))}
        </div>
      ) : data.items.length === 0 ? (
        <StateMessage
          title={hasActiveFilters(filters) ? "Нічого не знайдено" : "Каталог порожній"}
          action={
            hasActiveFilters(filters) && (
              <button className="button" onClick={() => setParams({})}>
                Скинути фільтри
              </button>
            )
          }
        >
          {hasActiveFilters(filters)
            ? "Спробуйте змінити запит або фільтри."
            : "Адміністратор ще не додав жодного фільму."}
        </StateMessage>
      ) : (
        <>
          <div className={`title-grid ${isPlaceholderData ? "title-grid--loading" : ""}`}>
            {data.items.map((title) => (
              <TitleCard key={title.id} title={title} />
            ))}
          </div>
          <Pagination page={data.page} pages={data.pages} onChange={changePage} />
        </>
      )}
    </section>
  );
}
