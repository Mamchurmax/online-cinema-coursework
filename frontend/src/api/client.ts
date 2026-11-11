/** Minimal fetch wrapper for the backend REST API (`/api/v1`). */

const API_PREFIX = "/api/v1";

export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : `HTTP ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

export type QueryParams = Record<string, string | number | boolean | string[] | number[] | undefined | null>;

/** Builds `?a=1&genre=2&genre=3`; arrays become repeated keys, empty values are skipped. */
export function toSearchParams(params: QueryParams): URLSearchParams {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    if (Array.isArray(value)) {
      value.forEach((item) => search.append(key, String(item)));
    } else {
      search.append(key, String(value));
    }
  }
  return search;
}

export async function apiGet<T>(path: string, params?: QueryParams, signal?: AbortSignal): Promise<T> {
  const query = params ? toSearchParams(params).toString() : "";
  const response = await fetch(`${API_PREFIX}${path}${query ? `?${query}` : ""}`, {
    headers: { Accept: "application/json" },
    signal,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, body?.detail ?? body);
  }
  return (await response.json()) as T;
}
