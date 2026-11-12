import { apiRequest } from "./client";
import type { User } from "./types";

export const authApi = {
  register: (email: string, password: string, displayName: string) =>
    apiRequest<User>("POST", "/auth/register", {
      json: { email, password, display_name: displayName },
    }),
  /** OAuth2 password flow: the email goes in the `username` field. */
  login: (email: string, password: string) =>
    apiRequest<{ access_token: string; token_type: "bearer" }>("POST", "/auth/login", {
      form: { username: email, password },
    }),
  me: (signal?: AbortSignal) => apiRequest<User>("GET", "/me", { signal }),
};
