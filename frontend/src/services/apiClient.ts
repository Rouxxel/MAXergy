/**
 * Typed fetch wrapper for the MAXergy FastAPI backend.
 *
 * Configure via Vite env vars:
 *   VITE_DEPLOYED_API_BASE_URL  e.g. https://maxergy-backend.com (checked first)
 *   VITE_API_BASE_URL           e.g. http://localhost:8000 (fallback)
 *   VITE_USE_MOCKS              "true" to short-circuit calls and return fixtures (default in dev)
 */

const BASE_URL =
  (import.meta.env.VITE_DEPLOYED_API_BASE_URL as string | undefined) ??
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
  "http://localhost:8000";

export const USE_MOCKS =
  (import.meta.env.VITE_USE_MOCKS as string | undefined) !== "false";

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
  retries?: number;
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export async function apiRequest<T>(
  path: string,
  { method = "GET", body, signal, retries = 2 }: RequestOptions = {},
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  let lastError: unknown;

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const res = await fetch(url, {
        method,
        signal,
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: body ? JSON.stringify(body) : undefined,
      });

      if (!res.ok) {
        const text = await res.text().catch(() => "");
        let parsed: unknown = text;
        try {
          parsed = JSON.parse(text);
        } catch {}
        throw new ApiError(
          `Request failed: ${res.status}`,
          res.status,
          parsed,
        );
      }

      return (await res.json()) as T;
    } catch (err) {
      lastError = err;
      if (err instanceof ApiError && err.status < 500) throw err;
      if (attempt < retries) await sleep(300 * 2 ** attempt);
    }
  }

  throw lastError instanceof Error
    ? lastError
    : new Error("Unknown network error");
}