// `||` (not `??`) so an empty string in .env (VITE_API_BASE_URL=) also falls
// back to the default — Vite exposes an unset-but-present key as "", which
// `??` would treat as a valid (and wrong) base URL.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** Shape of a FastAPI error response body. */
interface FastApiErrorBody {
  detail?: string | { msg: string }[];
}

async function parseErrorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as FastApiErrorBody;
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail.map((item) => item.msg).join("; ");
    }
  } catch {
    // Response body wasn't JSON (e.g. network-level error page); fall through.
  }
  return `Request failed with status ${response.status}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    throw new ApiError(await parseErrorMessage(response), response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path, { method: "GET" }),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PUT", body: body ? JSON.stringify(body) : undefined }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};

/** Build a query string from a params object, skipping empty values. */
export function buildQuery(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") {
      search.set(key, String(value));
    }
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}
