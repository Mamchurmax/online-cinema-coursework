import { apiGet } from "./client";
import type { CatalogFilters, Country, Genre, TitleDetail, TitlePage } from "./types";

export const catalogApi = {
  searchTitles: (filters: CatalogFilters, signal?: AbortSignal) =>
    apiGet<TitlePage>("/catalog/titles", { ...filters }, signal),
  getTitle: (id: number, signal?: AbortSignal) => apiGet<TitleDetail>(`/catalog/titles/${id}`, undefined, signal),
  listGenres: (signal?: AbortSignal) => apiGet<Genre[]>("/catalog/genres", undefined, signal),
  listCountries: (signal?: AbortSignal) => apiGet<Country[]>("/catalog/countries", undefined, signal),
};

export const healthApi = {
  check: (signal?: AbortSignal) => apiGet<{ status: string }>("/health", undefined, signal),
};
