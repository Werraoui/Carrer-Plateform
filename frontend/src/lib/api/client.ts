import axios, { type AxiosError } from "axios";

/** API backend — VITE_API_URL doit être défini au BUILD (Render). */
function resolveApiBase(): string {
  const fromEnv = import.meta.env.VITE_API_URL?.trim();
  if (fromEnv) return fromEnv.replace(/\/$/, "");

  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host !== "localhost" && host !== "127.0.0.1") {
      // Fallback prod si le build Render n'a pas reçu VITE_API_URL
      return "https://career-api-myoq.onrender.com";
    }
  }

  return "http://localhost:8000";
}

export const API_BASE = resolveApiBase();

export const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
  timeout: 120_000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("user");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

/** Message lisible depuis une erreur axios (validation FastAPI, réseau, etc.). */
export function formatApiError(err: unknown, fallback: string): string {
  if (!axios.isAxiosError(err)) {
    return fallback;
  }
  const ax = err as AxiosError<{ detail?: unknown }>;
  if (!ax.response) {
    if (ax.code === "ECONNABORTED") {
      return "Le serveur met trop de temps à répondre (cold start Render). Réessayez dans 30 s.";
    }
    return `Impossible de joindre l'API (${API_BASE}). Vérifiez VITE_API_URL sur Render.`;
  }
  const detail = ax.response.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => (typeof d === "object" && d && "msg" in d ? String((d as { msg: string }).msg) : String(d)))
      .join(" · ");
  }
  return fallback;
}
