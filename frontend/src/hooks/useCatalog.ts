import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { catalogApi } from "../api/catalog";
import type { CatalogFilters } from "../api/types";

export function useTitles(filters: CatalogFilters) {
  return useQuery({
    queryKey: ["titles", filters],
    queryFn: ({ signal }) => catalogApi.searchTitles(filters, signal),
    // Keep the previous page on screen while the next one loads (no flicker).
    placeholderData: keepPreviousData,
  });
}

export function useTitle(id: number) {
  return useQuery({
    queryKey: ["title", id],
    queryFn: ({ signal }) => catalogApi.getTitle(id, signal),
    enabled: Number.isInteger(id) && id > 0,
  });
}

/** Filter options change rarely, so they stay cached for the whole session. */
export function useGenres() {
  return useQuery({
    queryKey: ["genres"],
    queryFn: ({ signal }) => catalogApi.listGenres(signal),
    staleTime: Infinity,
  });
}

export function useCountries() {
  return useQuery({
    queryKey: ["countries"],
    queryFn: ({ signal }) => catalogApi.listCountries(signal),
    staleTime: Infinity,
  });
}
