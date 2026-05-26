import type {
  AddRatioRequest,
  BatchAddTickerResponse,
  GroupListItem,
  GroupResponse,
  RatioResponse,
} from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    let detail: string;
    try {
      const body = await res.json();
      detail = body?.detail ?? JSON.stringify(body);
    } catch {
      detail = await res.text();
    }
    throw new Error(`${res.status} ${res.statusText}: ${detail}`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  listGroups: () => request<GroupListItem[]>("/groups"),
  getGroup: (name: string, days = 120) =>
    request<GroupResponse>(`/groups/${encodeURIComponent(name)}?days=${days}`),
  addRatio: (payload: AddRatioRequest) =>
    request<RatioResponse>("/ratios", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  deleteRatio: (id: number) =>
    request<void>(`/ratios/${id}`, { method: "DELETE" }),
  deleteGroup: (name: string, cascade = false) =>
    request<void>(
      `/groups/${encodeURIComponent(name)}?cascade=${cascade ? "true" : "false"}`,
      { method: "DELETE" },
    ),
  renameGroup: (name: string, newName: string) =>
    request<{ group: string; updated: number }>(
      `/groups/${encodeURIComponent(name)}`,
      { method: "PATCH", body: JSON.stringify({ new_name: newName }) },
    ),
  reorderGroup: (name: string, ratioIds: number[]) =>
    request<void>(`/groups/${encodeURIComponent(name)}/order`, {
      method: "PUT",
      body: JSON.stringify({ ratio_ids: ratioIds }),
    }),
  setRatioPinned: (id: number, pinned: boolean) =>
    request<void>(`/ratios/${id}/pin`, {
      method: "PATCH",
      body: JSON.stringify({ pinned }),
    }),
  setGroupHidden: (name: string, hidden: boolean) =>
    request<void>(`/groups/${encodeURIComponent(name)}/visibility`, {
      method: "PATCH",
      body: JSON.stringify({ hidden }),
    }),
  addTickersBatch: (symbols: string[]) =>
    request<BatchAddTickerResponse>("/tickers/batch", {
      method: "POST",
      body: JSON.stringify({ ticker_symbols: symbols }),
    }),
};
