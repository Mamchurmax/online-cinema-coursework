import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In development the Vite server forwards /api to the backend, so the browser
// talks to one origin (no CORS). In Docker the same is done by nginx.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": process.env.VITE_API_PROXY_TARGET ?? "http://localhost:8000",
    },
  },
});
