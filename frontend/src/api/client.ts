const API_BASE =
  typeof window === "undefined"
    ? "http://127.0.0.1:8000"
    : `${window.location.protocol}//${window.location.hostname}:8000`;

let authTokenOverride = "";

export function getAuthToken(): string {
  return authTokenOverride;
}

export function setAuthToken(token: string): void {
  authTokenOverride = token;
}

export async function apiGet<T>(path: string): Promise<T> {
  const token = getAuthToken();
  const headers: Record<string, string> = {};
  if (token) headers["X-Workbench-Token"] = token;
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const token = getAuthToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["X-Workbench-Token"] = token;
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    credentials: "include",
    headers,
    body: body ? JSON.stringify(body) : undefined
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}
