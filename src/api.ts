/**
 * Typed API client.
 *
 * Token is read from localStorage on every call so the login screen
 * can set it without refreshing the module.
 */

import type {
  Agent,
  Annotation,
  Area,
  ArtifactSummary,
  Bug,
  BugFilters,
  BugListResponse,
  BugSummary,
  Platform,
  Product,
  Resolution,
  Severity,
} from "./types";

const TOKEN_KEY = "bugtracker_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

// ---------------------------------------------------------------------------
// Core fetch helper
// ---------------------------------------------------------------------------

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (
    options.body &&
    typeof options.body === "string" &&
    !headers["Content-Type"]
  ) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(path, { ...options, headers });

  if (res.status === 401) {
    clearToken();
    window.location.hash = "#/login";
    throw new ApiError(401, "Unauthorized");
  }

  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      msg = body.error ?? msg;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, msg);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Query string builder
// ---------------------------------------------------------------------------

function toQueryString(filters: BugFilters): string {
  const params = new URLSearchParams();
  if (filters.q) params.set("q", filters.q);
  if (filters.status) params.set("status", filters.status);
  if (filters.related_to) params.set("related_to", filters.related_to);
  if (filters.created_after) params.set("created_after", filters.created_after);
  if (filters.created_before)
    params.set("created_before", filters.created_before);
  if (filters.has_artifacts !== undefined)
    params.set("has_artifacts", String(filters.has_artifacts));
  filters.product?.forEach((v) => params.append("product", v));
  filters.area?.forEach((v) => params.append("area", v));
  filters.platform?.forEach((v) => params.append("platform", v));
  filters.priority?.forEach((v) => params.append("priority", String(v)));
  filters.severity?.forEach((v) => params.append("severity", v));
  filters.resolution?.forEach((v) => params.append("resolution", v));
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

// ---------------------------------------------------------------------------
// Bugs
// ---------------------------------------------------------------------------

export const bugs = {
  list(filters: BugFilters = {}): Promise<BugListResponse> {
    return apiFetch(`/bugs${toQueryString(filters)}`);
  },
  get(id: string): Promise<Bug> {
    return apiFetch(`/bugs/${id}`);
  },
  create(data: {
    product: string;
    title: string;
    description?: string;
    area?: string;
    platform?: string;
    priority?: number;
    severity?: string;
  }): Promise<BugSummary> {
    return apiFetch("/bugs", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },
  update(
    id: string,
    data: Partial<{
      product: string;
      title: string;
      description: string;
      area: string;
      platform: string;
      priority: number;
      severity: string;
    }>,
  ): Promise<BugSummary> {
    return apiFetch(`/bugs/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },
  close(
    id: string,
    resolution: Resolution,
    annotation?: string,
  ): Promise<{ bug: BugSummary; warnings?: string[] }> {
    return apiFetch(`/bugs/${id}/close`, {
      method: "POST",
      body: JSON.stringify({ resolution, annotation }),
    });
  },
  reopen(id: string): Promise<BugSummary> {
    return apiFetch(`/bugs/${id}/reopen`, { method: "POST" });
  },
};

// ---------------------------------------------------------------------------
// Annotations
// ---------------------------------------------------------------------------

export const annotations = {
  create(bugId: string, body: string): Promise<Annotation> {
    return apiFetch(`/bugs/${bugId}/annotations`, {
      method: "POST",
      body: JSON.stringify({ body }),
    });
  },
};

// ---------------------------------------------------------------------------
// Artifacts
// ---------------------------------------------------------------------------

export const artifacts = {
  upload(bugId: string, file: File): Promise<ArtifactSummary> {
    const fd = new FormData();
    fd.append("file", file);
    return apiFetch(`/bugs/${bugId}/artifacts`, { method: "POST", body: fd });
  },
};

// ---------------------------------------------------------------------------
// Relations
// ---------------------------------------------------------------------------

export const relations = {
  add(bugId: string, relatedId: string): Promise<{ bug_id: string; related_id: string }> {
    return apiFetch(`/bugs/${bugId}/relations`, {
      method: "POST",
      body: JSON.stringify({ related_id: relatedId }),
    });
  },
  remove(bugId: string, relatedId: string): Promise<void> {
    return apiFetch(`/bugs/${bugId}/relations/${relatedId}`, { method: "DELETE" });
  },
};

// ---------------------------------------------------------------------------
// Products
// ---------------------------------------------------------------------------

export const products = {
  list(includeArchived = false): Promise<Product[]> {
    return apiFetch(
      `/api/products${includeArchived ? "?include_archived=true" : ""}`,
    );
  },
  create(name: string, description?: string): Promise<Product> {
    return apiFetch("/api/products", {
      method: "POST",
      body: JSON.stringify({ name, description }),
    });
  },
  rename(oldName: string, newName: string): Promise<Product> {
    return apiFetch(`/api/products/${encodeURIComponent(oldName)}`, {
      method: "PATCH",
      body: JSON.stringify({ name: newName }),
    });
  },
  archive(name: string): Promise<Product> {
    return apiFetch(`/api/products/${encodeURIComponent(name)}`, {
      method: "PATCH",
      body: JSON.stringify({ archived: true }),
    });
  },
};

// ---------------------------------------------------------------------------
// Areas
// ---------------------------------------------------------------------------

export const areas = {
  list(includeArchived = false): Promise<Area[]> {
    return apiFetch(
      `/api/areas${includeArchived ? "?include_archived=true" : ""}`,
    );
  },
  create(name: string, description?: string): Promise<Area> {
    return apiFetch("/api/areas", {
      method: "POST",
      body: JSON.stringify({ name, description }),
    });
  },
  rename(oldName: string, newName: string): Promise<Area> {
    return apiFetch(`/api/areas/${encodeURIComponent(oldName)}`, {
      method: "PATCH",
      body: JSON.stringify({ name: newName }),
    });
  },
  archive(name: string): Promise<Area> {
    return apiFetch(`/api/areas/${encodeURIComponent(name)}`, {
      method: "PATCH",
      body: JSON.stringify({ archived: true }),
    });
  },
};

// ---------------------------------------------------------------------------
// Severities
// ---------------------------------------------------------------------------

export const severities = {
  list(includeArchived = false): Promise<Severity[]> {
    return apiFetch(
      `/api/severities${includeArchived ? "?include_archived=true" : ""}`,
    );
  },
  create(name: string, description?: string): Promise<Severity> {
    return apiFetch("/api/severities", {
      method: "POST",
      body: JSON.stringify({ name, description }),
    });
  },
  rename(oldName: string, newName: string): Promise<Severity> {
    return apiFetch(`/api/severities/${encodeURIComponent(oldName)}`, {
      method: "PATCH",
      body: JSON.stringify({ name: newName }),
    });
  },
  archive(name: string): Promise<Severity> {
    return apiFetch(`/api/severities/${encodeURIComponent(name)}`, {
      method: "PATCH",
      body: JSON.stringify({ archived: true }),
    });
  },
};

// ---------------------------------------------------------------------------
// Platforms
// ---------------------------------------------------------------------------

export const platforms = {
  list(includeArchived = false): Promise<Platform[]> {
    return apiFetch(
      `/api/platforms${includeArchived ? "?include_archived=true" : ""}`,
    );
  },
  create(name: string, description?: string): Promise<Platform> {
    return apiFetch("/api/platforms", {
      method: "POST",
      body: JSON.stringify({ name, description }),
    });
  },
  rename(oldName: string, newName: string): Promise<Platform> {
    return apiFetch(`/api/platforms/${encodeURIComponent(oldName)}`, {
      method: "PATCH",
      body: JSON.stringify({ name: newName }),
    });
  },
  archive(name: string): Promise<Platform> {
    return apiFetch(`/api/platforms/${encodeURIComponent(name)}`, {
      method: "PATCH",
      body: JSON.stringify({ archived: true }),
    });
  },
};

// ---------------------------------------------------------------------------
// Agents
// ---------------------------------------------------------------------------

export const agents = {
  list(): Promise<Agent[]> {
    return apiFetch("/agents");
  },
  register(
    name: string,
    description?: string,
    rate_limit?: number,
  ): Promise<Agent & { key: string }> {
    return apiFetch("/agents", {
      method: "POST",
      body: JSON.stringify({ name, description, rate_limit }),
    });
  },
  revoke(key: string): Promise<void> {
    return apiFetch(`/agents/${key}`, { method: "DELETE" });
  },
};

export { ApiError };
