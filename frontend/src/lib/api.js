const API_TOKEN_STORAGE_KEY = "sightline_api_token";

export async function fetchWorkspacePayload(caseId) {
  const query = `case_id=${encodeURIComponent(caseId)}`;
  const [graph, cases, records, resolution, graphStatus] = await Promise.all([
    fetchJson(`/app/graph-data?${query}`, "Graph data request failed"),
    fetchJson("/cases", "Cases request failed"),
    fetchJson(`/records/raw?${query}`, "Raw records request failed"),
    fetchJson(`/resolution/matches?${query}`, "Resolution request failed"),
    fetchJson(`/graph/status?${query}`, "Graph status request failed"),
  ]);

  return {
    graph,
    cases: cases.cases || [],
    records: records.records || [],
    resolution: resolution.resolution || null,
    graphStatus,
  };
}

export async function submitSourceRaw({ provider, sourceKind, caseId, query }) {
  const response = await fetch("/source/raw", {
    method: "POST",
    headers: buildJsonHeaders(),
    body: JSON.stringify({
      source: {
        source_id: `frontend-${provider}-${Date.now()}`,
        case_id: caseId.trim() || "default",
        provider,
        source_kind: sourceKind,
      },
      query,
    }),
  });

  if (response.ok) {
    return response.json();
  }

  const payload = await safeJson(response);
  const message = payload?.error?.message || `Raw source request failed with status ${response.status}.`;
  throw new Error(message);
}

export async function runFullSource({ provider, sourceKind, caseId, query }) {
  const response = await fetch("/source/full", {
    method: "POST",
    headers: buildJsonHeaders(),
    body: JSON.stringify({
      source: {
        source_id: `frontend-full-${provider}-${Date.now()}`,
        case_id: caseId.trim() || "default",
        provider,
        source_kind: sourceKind,
      },
      query,
    }),
  });

  if (response.ok) {
    return response.json();
  }

  const payload = await safeJson(response);
  const message = payload?.error?.message || `Full source request failed with status ${response.status}.`;
  throw new Error(message);
}

export async function rebuildGraph(caseId) {
  return fetchJson(
    `/graph/rebuild?case_id=${encodeURIComponent(caseId.trim() || "default")}`,
    "Graph rebuild failed",
    { method: "POST" },
  );
}

export function readApiToken() {
  try {
    return window.localStorage.getItem(API_TOKEN_STORAGE_KEY) || "";
  } catch {
    return "";
  }
}

export function writeApiToken(value) {
  try {
    window.localStorage.setItem(API_TOKEN_STORAGE_KEY, value.trim());
  } catch {
    return;
  }
}

async function fetchJson(url, failureMessage, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: buildHeaders(options.headers || {}),
  });
  if (response.ok) {
    return response.json();
  }

  const payload = await safeJson(response);
  const message = payload?.error?.message || `${failureMessage} with status ${response.status}.`;
  throw new Error(message);
}

async function safeJson(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

/**
 * @param {Record<string, string>} [extraHeaders]
 * @returns {Record<string, string>}
 */
function buildJsonHeaders(extraHeaders = {}) {
  return buildHeaders({
    "content-type": "application/json",
    ...extraHeaders,
  });
}

/**
 * @param {Record<string, string>} [extraHeaders]
 * @returns {Record<string, string>}
 */
function buildHeaders(extraHeaders = {}) {
  /** @type {Record<string, string>} */
  const headers = { ...extraHeaders };
  const apiToken = readApiToken();
  if (apiToken) {
    headers.authorization = `Bearer ${apiToken}`;
  }

  return headers;
}
