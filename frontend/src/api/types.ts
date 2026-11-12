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
  has_video: boolean;
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
  has_video: boolean;
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

export type UserRole = "user" | "admin";

export interface User {
  id: number;
  email: string;
  display_name: string;
  avatar_url: string | null;
  role: UserRole;
}

export interface PlaybackInfo {
  asset_id: number;
  master_url: string;
  duration_sec: number;
  qualities: string[];
  locked_qualities: string[];
  plan_code: string;
  plan_name: string;
  max_quality: string;
  ad: { name: string; url: string } | null;
  resume_position_sec: number;
}

export interface HistoryEntry {
  video_asset_id: number;
  title_id: number;
  title: string;
  type: TitleType;
  poster_url: string | null;
  backdrop_url: string | null;
  episode: { id: number; season_number: number; number: number; name: string } | null;
  progress_sec: number;
  duration_sec: number;
  completed: boolean;
  last_watched_at: string;
}
