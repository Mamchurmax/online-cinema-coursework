/** Minimal fetch wrapper for the backend REST API (`/api/v1`) with JWT support. */

export const API_PREFIX = "/api/v1";
const TOKEN_KEY = "cinema.accessToken";

export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : `HTTP ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

/** The access token lives in localStorage so a reload keeps the user signed in. */
type Listener = (token: string | null) => void;
const listeners = new Set<Listener>();

function readStoredToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null; // storage can be blocked (private mode, policies)
  }
}

let currentToken = readStoredToken();

export const tokenStore = {
  get: () => currentToken,
  set(token: string | null) {
    currentToken = token;
    try {
      if (token) localStorage.setItem(TOKEN_KEY, token);
      else localStorage.removeItem(TOKEN_KEY);
    } catch {
      // the session still works until the page is closed
    }
    listeners.forEach((listener) => listener(token));
  },
  subscribe(listener: Listener) {
    listeners.add(listener);
    return () => void listeners.delete(listener);
  },
};

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

interface RequestOptions {
  params?: QueryParams;
  json?: unknown;
  form?: Record<string, string>;
  signal?: AbortSignal;
  /** Lets the request finish after the page is closed (saving playback progress). */
  keepalive?: boolean;
}

export async function apiRequest<T>(method: string, path: string, options: RequestOptions = {}): Promise<T> {
  const { params, json, form, signal, keepalive } = options;
  const query = params ? toSearchParams(params).toString() : "";
  const headers: Record<string, string> = { Accept: "application/json" };
  const token = tokenStore.get();
  if (token) headers.Authorization = `Bearer ${token}`;

  let body: BodyInit | undefined;
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  } else if (form) {
    body = new URLSearchParams(form);
  }

  const response = await fetch(`${API_PREFIX}${path}${query ? `?${query}` : ""}`, {
    method,
    headers,
    body,
    signal,
    keepalive,
  });

  if (!response.ok) {
    const data = await response.json().catch(() => null);
    if (response.status === 401 && token) {
      tokenStore.set(null); // expired or revoked: sign out everywhere
    }
    throw new ApiError(response.status, data?.detail ?? data);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function apiGet<T>(path: string, params?: QueryParams, signal?: AbortSignal): Promise<T> {
  return apiRequest<T>("GET", path, { params, signal });
}
