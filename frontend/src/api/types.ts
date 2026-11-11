/** Types mirroring the backend Pydantic schemas (backend/app/schemas). */

export type TitleType = "movie" | "series";
export type CatalogSort = "rating" | "year" | "title" | "added";
export type SortOrder = "asc" | "desc";

export interface Genre {
  id: number;
  name: string;
}

export interface Country {
  code: string;
  name: string;
}

export interface Episode {
  id: number;
  number: number;
  name: string;
  description: string;
  duration: number | null;
}

export interface Season {
  id: number;
  number: number;
  name: string;
  episodes: Episode[];
}

export interface TitleListItem {
  id: number;
  type: TitleType;
  title: string;
  release_year: number | null;
  rating: string | null; // Decimal is serialised as a string, e.g. "8.2"
  poster_url: string | null;
  genres: Genre[];
}

export interface TitleDetail extends TitleListItem {
  description: string;
  backdrop_url: string | null;
  duration: number | null;
  countries: Country[];
  seasons: Season[];
}

export interface TitlePage {
  items: TitleListItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface CatalogFilters {
  q?: string;
  type?: TitleType;
  genre?: number[];
  country?: string[];
  year_from?: number;
  year_to?: number;
  min_rating?: number;
  sort?: CatalogSort;
  order?: SortOrder;
  page?: number;
  page_size?: number;
}
