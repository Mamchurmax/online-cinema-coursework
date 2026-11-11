/**
 * Catalog filters live in the URL (?q=...&genre=1&genre=2&page=2), so a search
 * can be bookmarked, shared and restored with the browser's Back button.
 */
import type { CatalogFilters, CatalogSort, SortOrder, TitleType } from "../../api/types";

export const PAGE_SIZE = 24;

export const SORT_OPTIONS: { value: `${CatalogSort}:${SortOrder}`; label: string }[] = [
  { value: "rating:desc", label: "За рейтингом" },
  { value: "year:desc", label: "Спершу нові" },
  { value: "year:asc", label: "Спершу старі" },
  { value: "title:asc", label: "За назвою (А–Я)" },
  { value: "added:desc", label: "Нещодавно додані" },
];

const TITLE_TYPES: TitleType[] = ["movie", "series"];
const SORTS: CatalogSort[] = ["rating", "year", "title", "added"];
const ORDERS: SortOrder[] = ["asc", "desc"];

function toInt(value: string | null): number | undefined {
  if (value === null || value.trim() === "") return undefined;
  const number = Number(value);
  return Number.isInteger(number) ? number : undefined;
}

/** Years outside the range the API accepts are ignored instead of causing an error. */
function toYear(value: string | null): number | undefined {
  const year = toInt(value);
  return year !== undefined && year >= 1870 && year <= 2100 ? year : undefined;
}

function oneOf<T extends string>(value: string | null, allowed: T[]): T | undefined {
  return allowed.includes(value as T) ? (value as T) : undefined;
}

export function filtersFromParams(params: URLSearchParams): CatalogFilters {
  let yearFrom = toYear(params.get("year_from"));
  let yearTo = toYear(params.get("year_to"));
  if (yearFrom !== undefined && yearTo !== undefined && yearFrom > yearTo) {
    [yearFrom, yearTo] = [yearTo, yearFrom]; // the API rejects an inverted range
  }

  return {
    q: params.get("q")?.trim() || undefined,
    type: oneOf(params.get("type"), TITLE_TYPES),
    genre: params.getAll("genre").map(Number).filter(Number.isInteger),
    country: params.getAll("country").filter(Boolean),
    year_from: yearFrom,
    year_to: yearTo,
    sort: oneOf(params.get("sort"), SORTS) ?? "rating",
    order: oneOf(params.get("order"), ORDERS) ?? "desc",
    page: Math.max(toInt(params.get("page")) ?? 1, 1),
    page_size: PAGE_SIZE,
  };
}

/** Writes filters back to the URL, omitting defaults to keep links short. */
export function filtersToParams(filters: CatalogFilters): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.q) params.set("q", filters.q);
  if (filters.type) params.set("type", filters.type);
  filters.genre?.forEach((id) => params.append("genre", String(id)));
  filters.country?.forEach((code) => params.append("country", code));
  if (filters.year_from !== undefined) params.set("year_from", String(filters.year_from));
  if (filters.year_to !== undefined) params.set("year_to", String(filters.year_to));
  if (filters.sort && filters.sort !== "rating") params.set("sort", filters.sort);
  if (filters.order && filters.order !== "desc") params.set("order", filters.order);
  if (filters.page && filters.page > 1) params.set("page", String(filters.page));
  return params;
}

export function hasActiveFilters(filters: CatalogFilters): boolean {
  return Boolean(
    filters.q ||
      filters.type ||
      filters.genre?.length ||
      filters.country?.length ||
      filters.year_from !== undefined ||
      filters.year_to !== undefined,
  );
}
