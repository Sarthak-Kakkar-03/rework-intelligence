import type { ApiResponses } from "@/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function apiGet<Path extends keyof ApiResponses>(
  path: Path,
  init?: RequestInit,
): Promise<ApiResponses[Path]> {
  const url = `${API_BASE_URL}${path}`;

  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");

  const requestOptions: RequestInit = {
    ...init,
    headers: headers,
  };

  const response = await fetch(url, requestOptions);

  if (!response.ok) {
    throw new Error(`GET ${path} failed with ${response.status}`);
  }

  const data = await response.json();
  return data as ApiResponses[Path];
}
