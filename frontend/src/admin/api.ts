import { apiGet, apiRequest } from "../api/client";
import type { Episode, Plan, Season, TitleDetail, TitleType } from "../api/types";

export interface TitleInput {
  type: TitleType;
  title: string;
  description: string;
  release_year: number | null;
  rating: string | null;
  poster_url: string | null;
  backdrop_url: string | null;
  duration: number | null;
  genre_ids: number[];
  country_codes: string[];
}

export interface EpisodeInput {
  number: number;
  name: string;
  description: string;
  duration: number | null;
}

export interface Stream {
  directory: string;
  hls_path: string;
  qualities: string[];
  duration_sec: number;
}

export interface AdminVideo {
  id: number;
  hls_path: string;
  qualities: string[];
  duration_sec: number;
  title_id: number;
  title: string;
  episode_label: string | null;
}

export interface AdminUser {
  id: number;
  email: string;
  display_name: string;
  role: "user" | "admin";
  created_at: string;
}

export interface AdminAd {
  id: number;
  name: string;
  hls_path: string;
  active: boolean;
}

export interface PendingPayment {
  id: number;
  amount: string;
  scenario: string;
  status: string;
  created_at: string;
  plan: Plan;
  user_email: string;
}

export type ReportCell = string | number;
export type ValueFormat = "number" | "money" | "percent" | "hours";

export interface ReportInfo {
  code: string;
  title: string;
  description: string;
}

export interface ReportChart {
  key: string;
  title: string;
  kind: "bar" | "hbar" | "line" | "pie";
  x_key: string;
  series: { key: string; label: string }[];
  data: Record<string, ReportCell>[];
}

export interface Report {
  code: string;
  title: string;
  period: { start: string; end: string };
  generated_at: string;
  metrics: { key: string; label: string; value: number; format: ValueFormat }[];
  charts: ReportChart[];
  table: {
    title: string;
    columns: { key: string; label: string; format: ValueFormat | "text" }[];
    rows: Record<string, ReportCell>[];
  } | null;
  notes: string[];
}

export type PlanInput = Pick<Plan, "name" | "price" | "period_days" | "max_quality" | "has_ads">;

export const adminApi = {
  createTitle: (body: TitleInput) => apiRequest<TitleDetail>("POST", "/admin/titles", { json: body }),
  updateTitle: (id: number, body: TitleInput) =>
    apiRequest<TitleDetail>("PUT", `/admin/titles/${id}`, { json: body }),
  deleteTitle: (id: number) => apiRequest<void>("DELETE", `/admin/titles/${id}`),
  importTitle: (tmdbId: number, type: TitleType) =>
    apiRequest<TitleDetail>("POST", "/admin/titles/import", { json: { tmdb_id: tmdbId, type } }),

  addSeason: (titleId: number, number: number, name: string) =>
    apiRequest<Season>("POST", `/admin/titles/${titleId}/seasons`, { json: { number, name } }),
  deleteSeason: (id: number) => apiRequest<void>("DELETE", `/admin/seasons/${id}`),
  addEpisode: (seasonId: number, body: EpisodeInput) =>
    apiRequest<Episode>("POST", `/admin/seasons/${seasonId}/episodes`, { json: body }),
  deleteEpisode: (id: number) => apiRequest<void>("DELETE", `/admin/episodes/${id}`),

  streams: () => apiGet<Stream[]>("/admin/streams"),
  videos: () => apiGet<AdminVideo[]>("/admin/videos"),
  attachTitleVideo: (titleId: number, streamDir: string) =>
    apiRequest<AdminVideo>("PUT", `/admin/titles/${titleId}/video`, { json: { stream_dir: streamDir } }),
  attachEpisodeVideo: (episodeId: number, streamDir: string) =>
    apiRequest<AdminVideo>("PUT", `/admin/episodes/${episodeId}/video`, { json: { stream_dir: streamDir } }),
  detachVideo: (id: number) => apiRequest<void>("DELETE", `/admin/videos/${id}`),

  ads: () => apiGet<AdminAd[]>("/admin/ads"),
  createAd: (name: string, streamDir: string) =>
    apiRequest<AdminAd>("POST", "/admin/ads", { json: { name, stream_dir: streamDir } }),
  setAdActive: (id: number, active: boolean) =>
    apiRequest<AdminAd>("PATCH", `/admin/ads/${id}`, { json: { active } }),

  updatePlan: (id: number, body: PlanInput) => apiRequest<Plan>("PUT", `/admin/plans/${id}`, { json: body }),

  users: (q: string, page: number) =>
    apiGet<{ items: AdminUser[]; total: number; page: number; page_size: number }>("/admin/users", {
      q,
      page,
      page_size: 20,
    }),
  setRole: (id: number, role: AdminUser["role"]) =>
    apiRequest<AdminUser>("PATCH", `/admin/users/${id}`, { json: { role } }),
  deleteUser: (id: number) => apiRequest<void>("DELETE", `/admin/users/${id}`),

  pendingPayments: () => apiGet<PendingPayment[]>("/admin/payments/pending"),
  resolvePayment: (id: number, approved: boolean) =>
    apiRequest<unknown>("POST", `/admin/payments/${id}/resolve`, { json: { approved } }),

  reports: () => apiGet<ReportInfo[]>("/admin/reports"),
  report: (code: string, dateFrom: string, dateTo: string) =>
    apiGet<Report>(`/admin/reports/${code}`, { date_from: dateFrom, date_to: dateTo }),
};

/** Human-readable text of an API error for admin forms. */
export function errorText(error: unknown): string {
  const detail = (error as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return `Перевірте поля: ${detail[0].loc?.at(-1)} — ${detail[0].msg}`;
  return "Не вдалося виконати дію.";
}
