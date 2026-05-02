import { useEffect, useState } from "react";

const CSV_EXAMPLE = JSON.stringify(
  [
    {
      full_name: "Maya Patel",
      email: "maya.patel@gmail.com",
      phone: "3175550101",
      company_name: "OpenAI LLC",
    },
  ],
  null,
  2,
);

const PROVIDER_OPTIONS = [
  { provider: "ipinfo", sourceKind: "api", label: "IPinfo", placeholder: "8.8.8.8" },
  { provider: "crt.sh", sourceKind: "scraper", label: "crt.sh", placeholder: "example.com" },
  { provider: "nominatim", sourceKind: "api", label: "Nominatim", placeholder: "Indianapolis" },
  { provider: "opensky", sourceKind: "api", label: "OpenSky", placeholder: "AAL123" },
];

function App() {
  const [caseId, setCaseId] = useState("default");
  const [graph, setGraph] = useState(null);
  const [cases, setCases] = useState([]);
  const [records, setRecords] = useState([]);
  const [resolution, setResolution] = useState(null);
  const [graphStatus, setGraphStatus] = useState(null);
  const [apiToken, setApiToken] = useState(readApiToken());
  const [selectedNodeId, setSelectedNodeId] = useState("");
  const [isPulsing, setIsPulsing] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [intakeMessage, setIntakeMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [manualForm, setManualForm] = useState(createEmptyManualForm());
  const [providerForm, setProviderForm] = useState(createDefaultProviderForm());
  const [csvRowsText, setCsvRowsText] = useState(CSV_EXAMPLE);

  useEffect(() => {
    let isMounted = true;

    async function loadWorkspace() {
      try {
        const payload = await fetchWorkspacePayload("default");
        if (!isMounted) {
          return;
        }

        applyWorkspacePayload(payload);
      } catch (error) {
        if (!isMounted) {
          return;
        }

        setErrorMessage(String(error));
      }
    }

    loadWorkspace();

    return () => {
      isMounted = false;
    };
  }, []);

  function applyWorkspacePayload(payload) {
    setGraph(payload.graph);
    setCases(payload.cases);
    setRecords(payload.records);
    setResolution(payload.resolution);
    setGraphStatus(payload.graphStatus);
    setSelectedNodeId(payload.graph.nodes[0]?.id || "");
  }

  async function reloadWorkspace(targetCaseId = caseId) {
    const cleanedCaseId = targetCaseId.trim() || "default";
    setCaseId(cleanedCaseId);
    const payload = await fetchWorkspacePayload(cleanedCaseId);
    applyWorkspacePayload(payload);
  }

  function updateManualField(fieldName, value) {
    setManualForm((currentForm) => ({
      ...currentForm,
      [fieldName]: value,
    }));
  }

  function updateProviderField(fieldName, value) {
    setProviderForm((currentForm) => ({
      ...currentForm,
      [fieldName]: value,
    }));
  }

  function updateApiToken(value) {
    setApiToken(value);
    writeApiToken(value);
  }

  async function handleManualSubmit(event) {
    event.preventDefault();

    const query = buildManualQuery(manualForm);
    if (!query.note) {
      setIntakeMessage("Manual records need a note before they can be saved.");
      return;
    }

    const didSave = await saveRawRecord({
      provider: "manual_input",
      sourceKind: "manual",
      caseId,
      query,
      successMessage: "Manual raw record saved and graph refreshed.",
    });
    if (didSave) {
      setManualForm(createEmptyManualForm());
    }
  }

  async function handleCsvImport(event) {
    event.preventDefault();

    let rows;
    try {
      rows = JSON.parse(csvRowsText);
    } catch (error) {
      setIntakeMessage(`CSV import must be a JSON array of row objects. ${error}`);
      return;
    }

    if (!Array.isArray(rows)) {
      setIntakeMessage("CSV import must be a JSON array.");
      return;
    }

    if (!rows.every((row) => row && typeof row === "object" && !Array.isArray(row))) {
      setIntakeMessage("Every CSV import row must be an object.");
      return;
    }

    await saveRawRecord({
      provider: "csv_upload",
      sourceKind: "csv",
      caseId,
      query: rows,
      successMessage: `${rows.length} imported rows saved and graph refreshed.`,
    });
  }

  async function handleProviderRun(event) {
    event.preventDefault();
    setIsSubmitting(true);
    setIntakeMessage("");

    try {
      const providerOption = getProviderOption(providerForm.provider);
      const query = buildProviderQuery(providerForm.queryText);
      await runFullSource({
        provider: providerOption.provider,
        sourceKind: providerOption.sourceKind,
        caseId,
        query,
      });
      await reloadWorkspace(caseId);
      setIntakeMessage(`${providerOption.label} ran through the full pipeline.`);
    } catch (error) {
      setIntakeMessage(String(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleGraphRebuild() {
    setIsSubmitting(true);
    try {
      await rebuildGraph(caseId);
      await reloadWorkspace(caseId);
      setIntakeMessage("Graph repository rebuilt from saved raw records.");
    } catch (error) {
      setIntakeMessage(String(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function saveRawRecord({ provider, sourceKind, caseId, query, successMessage }) {
    setIsSubmitting(true);
    setIntakeMessage("");
    setErrorMessage("");

    try {
      await submitSourceRaw({ provider, sourceKind, caseId, query });
      await reloadWorkspace(caseId);
      setIntakeMessage(successMessage);
      return true;
    } catch (error) {
      setIntakeMessage(String(error));
      return false;
    } finally {
      setIsSubmitting(false);
    }
  }

  let selectedNode = null;
  if (graph && selectedNodeId) {
    selectedNode = graph.nodes.find((node) => node.id === selectedNodeId) || null;
  }

  let selectedEdges = [];
  if (graph && selectedNode) {
    selectedEdges = graph.edges.filter(
      (edge) => edge.from === selectedNode.id || edge.to === selectedNode.id,
    );
  }

  if (errorMessage) {
    return (
      <div className="shell">
        <main className="workspace workspace-error">
          <div className="workspace-bar">
            <div>
              <p className="eyebrow">Sightline Fusion</p>
              <h1 className="brand-title">Workspace unavailable</h1>
            </div>
          </div>
          <section className="graph-frame">
            <div className="error-card">{errorMessage}</div>
          </section>
        </main>
      </div>
    );
  }

  if (!graph) {
    return (
      <div className="shell">
        <main className="workspace workspace-error">
          <div className="workspace-bar">
            <div>
              <p className="eyebrow">Sightline Fusion</p>
              <h1 className="brand-title">Loading workspace</h1>
            </div>
          </div>
          <section className="graph-frame">
            <div className="error-card">Loading graph data...</div>
          </section>
        </main>
      </div>
    );
  }

  return (
    <div className="shell">
      <LeftPanel
        caseId={caseId}
        cases={cases}
        graph={graph}
        graphStatus={graphStatus}
        apiToken={apiToken}
        manualForm={manualForm}
        providerForm={providerForm}
        csvRowsText={csvRowsText}
        intakeMessage={intakeMessage}
        isSubmitting={isSubmitting}
        onCaseIdChange={setCaseId}
        onApiTokenChange={updateApiToken}
        onCaseRefresh={() => reloadWorkspace(caseId)}
        onGraphRebuild={handleGraphRebuild}
        onManualFieldChange={updateManualField}
        onManualSubmit={handleManualSubmit}
        onProviderFieldChange={updateProviderField}
        onProviderRun={handleProviderRun}
        onCsvRowsTextChange={setCsvRowsText}
        onCsvImport={handleCsvImport}
        onRefreshGraph={() => reloadWorkspace(caseId)}
      />
      <main className="workspace">
        <header className="workspace-bar">
          <div>
            <p className="eyebrow">Graph View</p>
            <h1 className="brand-title">{graph.title}</h1>
          </div>
          <div className="toolbar">
            <button
              className="toolbar-button"
              type="button"
              onClick={() => setSelectedNodeId(graph.nodes[0]?.id || "")}
            >
              Recenter
            </button>
            <button
              className="toolbar-button"
              type="button"
              onClick={() => setIsPulsing((currentValue) => !currentValue)}
            >
              {isPulsing ? "Stop Pulse" : "Pulse Links"}
            </button>
          </div>
        </header>

        <GraphCanvas
          graph={graph}
          selectedNodeId={selectedNodeId}
          onSelectNode={setSelectedNodeId}
          isPulsing={isPulsing}
        />
      </main>
      <RightPanel
        graph={graph}
        selectedNode={selectedNode}
        selectedEdges={selectedEdges}
        resolution={resolution}
        records={records}
      />
    </div>
  );
}

function LeftPanel({
  caseId,
  cases,
  graph,
  graphStatus,
  apiToken,
  manualForm,
  providerForm,
  csvRowsText,
  intakeMessage,
  isSubmitting,
  onCaseIdChange,
  onApiTokenChange,
  onCaseRefresh,
  onGraphRebuild,
  onManualFieldChange,
  onManualSubmit,
  onProviderFieldChange,
  onProviderRun,
  onCsvRowsTextChange,
  onCsvImport,
  onRefreshGraph,
}) {
  return (
    <aside className="panel panel-left">
      <div className="panel-block brand-block">
        <p className="eyebrow">Sightline Fusion</p>
        <h2 className="brand-title">Investigation Workspace</h2>
        <p className="brand-copy">
          A graph-native workspace for linking identities, infrastructure, and evidence with analyst context.
        </p>
      </div>

      <div className="panel-block">
        <div className="section-heading">
          <h2>Case Control</h2>
          <span className="section-kicker">Scope</span>
        </div>
        <div className="intake-form">
          <label>
            Case ID
            <input
              value={caseId}
              onChange={(event) => onCaseIdChange(event.target.value)}
              placeholder="default"
            />
          </label>
          <label>
            API token
            <input
              value={apiToken}
              onChange={(event) => onApiTokenChange(event.target.value)}
              placeholder="Only needed when API_AUTH_TOKEN is set"
            />
          </label>
          <div className="intake-actions">
            <button className="toolbar-button" type="button" onClick={onCaseRefresh} disabled={isSubmitting}>
              Load Case
            </button>
            <button className="toolbar-button" type="button" onClick={onGraphRebuild} disabled={isSubmitting}>
              Rebuild Graph
            </button>
          </div>
          <p className="mini-copy">
            Graph storage: {graphStatus?.graph_repository_kind || "memory"} · {graphStatus?.nodes || 0} nodes
          </p>
        </div>
        <div className="case-list">
          {cases.map((item) => (
            <button
              key={item.case_id}
              className="case-chip"
              type="button"
              onClick={() => onCaseIdChange(item.case_id)}
            >
              {item.case_id} · {item.record_count}
            </button>
          ))}
        </div>
      </div>

      <div className="panel-block">
        <div className="section-heading">
          <h2>Provider Run</h2>
          <span className="section-kicker">Full Pipeline</span>
        </div>
        <form className="intake-form" onSubmit={onProviderRun}>
          <label>
            Provider
            <select
              value={providerForm.provider}
              onChange={(event) => onProviderFieldChange("provider", event.target.value)}
            >
              {PROVIDER_OPTIONS.map((option) => (
                <option key={option.provider} value={option.provider}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Query
            <textarea
              value={providerForm.queryText}
              onChange={(event) => onProviderFieldChange("queryText", event.target.value)}
              placeholder={getProviderOption(providerForm.provider).placeholder}
              rows={3}
            />
          </label>
          <button className="toolbar-button" type="submit" disabled={isSubmitting}>
            Run Full Pipeline
          </button>
        </form>
      </div>

      <div className="panel-block">
        <div className="section-heading">
          <h2>Raw Intake</h2>
          <span className="section-kicker">Save First</span>
        </div>
        <form className="intake-form" onSubmit={onManualSubmit}>
          <label>
            Note
            <textarea
              value={manualForm.note}
              onChange={(event) => onManualFieldChange("note", event.target.value)}
              placeholder="Why this record matters"
              rows={3}
            />
          </label>
          <label>
            Full name
            <input
              value={manualForm.full_name}
              onChange={(event) => onManualFieldChange("full_name", event.target.value)}
              placeholder="Alice Ng"
            />
          </label>
          <label>
            Email
            <input
              value={manualForm.email}
              onChange={(event) => onManualFieldChange("email", event.target.value)}
              placeholder="alice@example.org"
            />
          </label>
          <label>
            Phone
            <input
              value={manualForm.phone}
              onChange={(event) => onManualFieldChange("phone", event.target.value)}
              placeholder="+1 317 555 0101"
            />
          </label>
          <label>
            Company
            <input
              value={manualForm.company_name}
              onChange={(event) => onManualFieldChange("company_name", event.target.value)}
              placeholder="OpenAI LLC"
            />
          </label>
          <div className="intake-actions">
            <button className="toolbar-button" type="submit" disabled={isSubmitting}>
              Save Manual
            </button>
            <button className="toolbar-button" type="button" onClick={onRefreshGraph} disabled={isSubmitting}>
              Refresh
            </button>
          </div>
        </form>
        {intakeMessage ? <p className="intake-message">{intakeMessage}</p> : null}
      </div>

      <div className="panel-block">
        <div className="section-heading">
          <h2>Import Rows</h2>
          <span className="section-kicker">JSON CSV</span>
        </div>
        <form className="intake-form" onSubmit={onCsvImport}>
          <label>
            Rows
            <textarea
              className="code-textarea"
              value={csvRowsText}
              onChange={(event) => onCsvRowsTextChange(event.target.value)}
              rows={7}
            />
          </label>
          <button className="toolbar-button" type="submit" disabled={isSubmitting}>
            Import Rows
          </button>
        </form>
      </div>

      <div className="panel-block">
        <div className="section-heading">
          <h2>Case Snapshot</h2>
          <span className="status-pill">{graph.case.status}</span>
        </div>
        <dl className="stat-grid">
          <SummaryCard label="Case" value={graph.case.caseId} />
          <SummaryCard label="Scope" value={graph.case.scope} />
          <SummaryCard label="Nodes" value={String(graph.nodes.length)} />
          <SummaryCard label="Edges" value={String(graph.edges.length)} />
        </dl>
      </div>

      <div className="panel-block">
        <div className="section-heading">
          <h2>Legend</h2>
          <span className="section-kicker">Node Types</span>
        </div>
        <div className="legend-list">
          {graph.legend.map((item) => (
            <div key={item.label} className="legend-item">
              <span className="legend-swatch" style={{ background: item.color }} />
              <div>
                <strong>{item.label}</strong>
                <div>{item.description}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="panel-block">
        <div className="section-heading">
          <h2>Signals</h2>
          <span className="section-kicker">Confidence</span>
        </div>
        <ul className="signal-list">
          <li>
            <span className="signal-band band-high" />
            High confidence relationships
          </li>
          <li>
            <span className="signal-band band-medium" />
            Investigative leads
          </li>
          <li>
            <span className="signal-band band-low" />
            Weak contextual links
          </li>
        </ul>
      </div>
    </aside>
  );
}

function RightPanel({ graph, selectedNode, selectedEdges, resolution, records }) {
  return (
    <aside className="panel panel-right">
      <div className="panel-block">
        <div className="section-heading">
          <h2>Selected Node</h2>
          <span className="section-kicker">Details</span>
        </div>
        {!selectedNode ? (
          <p className="empty-state">Choose a node from the graph.</p>
        ) : (
          <div className="selected-card">
            <p className="eyebrow">Selected</p>
            <h3 className="selected-title">{selectedNode.label}</h3>
            <div className="selected-meta">
              <span className="meta-chip">{selectedNode.type}</span>
              <span className="meta-chip">{selectedNode.tier}</span>
              <span className="meta-chip">{selectedNode.status}</span>
            </div>
            <p className="selected-copy">{selectedNode.description}</p>
            <div className="selected-attrs">
              {selectedNode.attributes.map((attribute) => (
                <span key={attribute} className="attr-chip">
                  {attribute}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="panel-block">
        <div className="section-heading">
          <h2>Resolution</h2>
          <span className="section-kicker">Review Queue</span>
        </div>
        {!resolution ? (
          <p className="empty-state">No resolution data loaded.</p>
        ) : (
          <>
            <dl className="stat-grid">
              <SummaryCard label="Candidates" value={String(resolution.candidate_count)} />
              <SummaryCard label="Compared" value={String(resolution.comparison_count)} />
              <SummaryCard label="Merge" value={String(resolution.summary?.merge || 0)} />
              <SummaryCard label="Review" value={String(resolution.summary?.review_needed || 0)} />
            </dl>
            <ul className="activity-list compact-list">
              {resolution.matches?.slice(0, 4).map((match) => (
                <li key={`${match.left_record_id}-${match.right_record_id}`} className="activity-item">
                  <span className="activity-time">{match.confidence_percent}%</span>
                  <div className="activity-copy">
                    {match.decision}: {match.left_record_id} ↔ {match.right_record_id}
                  </div>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>

      <div className="panel-block">
        <div className="section-heading">
          <h2>Saved Records</h2>
          <span className="section-kicker">{records.length}</span>
        </div>
        {!records.length ? (
          <p className="empty-state">No raw records saved for this case.</p>
        ) : (
          <ul className="activity-list compact-list">
            {records.slice(0, 6).map((record) => (
              <li key={record.record_id} className="activity-item">
                <span className="activity-time">{record.provider}</span>
                <div className="activity-copy">
                  {record.status} · {record.record_id.slice(0, 8)}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="panel-block">
        <div className="section-heading">
          <h2>Connected Links</h2>
          <span className="section-kicker">Edges</span>
        </div>
        {!selectedNode || !selectedEdges.length ? (
          <p className="empty-state">No node selected.</p>
        ) : (
          <ul className="connection-list">
            {selectedEdges.map((edge) => {
              const otherNodeId = edge.from === selectedNode.id ? edge.to : edge.from;
              const otherNode = graph.nodes.find((node) => node.id === otherNodeId);
              if (!otherNode) {
                return null;
              }

              return (
                <li key={`${edge.from}-${edge.to}-${edge.label}`} className="connection-item">
                  <span className="legend-swatch" style={{ background: otherNode.color }} />
                  <div>
                    <strong>{edge.label}</strong>
                    <div>
                      {otherNode.label} · {otherNode.type}
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <div className="panel-block">
        <div className="section-heading">
          <h2>Analyst Notes</h2>
          <span className="section-kicker">Activity</span>
        </div>
        <ul className="activity-list">
          {graph.activity.map((item) => (
            <li key={`${item.time}-${item.text}`} className="activity-item">
              <span className="activity-time">{item.time}</span>
              <div className="activity-copy">{item.text}</div>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}

function GraphCanvas({ graph, selectedNodeId, onSelectNode, isPulsing }) {
  return (
    <section className={`graph-frame ${isPulsing ? "is-pulsing" : ""}`}>
      <div className="graph-overlay graph-overlay-top">
        <span>Obsidian-style spatial graph</span>
        <span>
          {graph.nodes.length} nodes / {graph.edges.length} edges
        </span>
      </div>
      <svg
        id="graph-canvas"
        className="graph-canvas"
        viewBox="0 0 1200 760"
        role="img"
        aria-label="Investigation graph"
      >
        <defs>
          <filter id="nodeGlow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="6" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <g className="edge-layer">
          {graph.edges.map((edge) => {
            const fromNode = graph.nodes.find((node) => node.id === edge.from);
            const toNode = graph.nodes.find((node) => node.id === edge.to);

            if (!fromNode || !toNode) {
              return null;
            }

            const centerX = (fromNode.x + toNode.x) / 2;
            const centerY = (fromNode.y + toNode.y) / 2;

            return (
              <g key={`${edge.from}-${edge.to}-${edge.label}`}>
                <line
                  className={`edge-line ${getConfidenceClass(edge.confidence)}`}
                  x1={fromNode.x}
                  y1={fromNode.y}
                  x2={toNode.x}
                  y2={toNode.y}
                />
                <text className="edge-label" x={centerX} y={centerY - 8}>
                  {edge.label}
                </text>
              </g>
            );
          })}
        </g>

        <g className="node-layer">
          {graph.nodes.map((node) => {
            const isSelected = node.id === selectedNodeId;

            return (
              <g key={node.id} className="node-group" onClick={() => onSelectNode(node.id)}>
                <circle
                  className={isSelected ? "node-circle is-selected" : "node-circle"}
                  cx={node.x}
                  cy={node.y}
                  r={node.radius}
                  fill={node.color}
                  filter="url(#nodeGlow)"
                />
                <text className="node-label" x={node.x} y={node.y + node.radius + 24}>
                  {node.label}
                </text>
                <text className="node-subtitle" x={node.x} y={node.y + node.radius + 40}>
                  {node.type}
                </text>
              </g>
            );
          })}
        </g>
      </svg>
      <div className="graph-overlay graph-overlay-bottom">
        <span>Click a node to inspect it</span>
        <span>Palantir-inspired command center styling</span>
      </div>
    </section>
  );
}

function SummaryCard({ label, value }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function getConfidenceClass(confidence) {
  if (confidence >= 90) {
    return "edge-high";
  }

  if (confidence >= 70) {
    return "edge-medium";
  }

  return "edge-low";
}

function createEmptyManualForm() {
  return {
    note: "",
    full_name: "",
    email: "",
    phone: "",
    company_name: "",
  };
}

function createDefaultProviderForm() {
  return {
    provider: "ipinfo",
    queryText: "8.8.8.8",
  };
}

function buildManualQuery(form) {
  const query = {};

  for (const [key, value] of Object.entries(form)) {
    const cleanedValue = value.trim();
    if (!cleanedValue) {
      continue;
    }

    query[key] = cleanedValue;
  }

  return query;
}

function buildProviderQuery(queryText) {
  const cleanedValue = queryText.trim();
  if (!cleanedValue) {
    throw new Error("Provider query is required.");
  }

  if (cleanedValue.startsWith("{") || cleanedValue.startsWith("[")) {
    return JSON.parse(cleanedValue);
  }

  return cleanedValue;
}

function getProviderOption(provider) {
  return PROVIDER_OPTIONS.find((option) => option.provider === provider) || PROVIDER_OPTIONS[0];
}

async function fetchWorkspacePayload(caseId) {
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

async function submitSourceRaw({ provider, sourceKind, caseId, query }) {
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

async function runFullSource({ provider, sourceKind, caseId, query }) {
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

async function rebuildGraph(caseId) {
  return fetchJson(
    `/graph/rebuild?case_id=${encodeURIComponent(caseId.trim() || "default")}`,
    "Graph rebuild failed",
    { method: "POST" },
  );
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

function buildJsonHeaders(extraHeaders = {}) {
  return buildHeaders({
    "content-type": "application/json",
    ...extraHeaders,
  });
}

function buildHeaders(extraHeaders = {}) {
  const headers = { ...extraHeaders };
  const apiToken = readApiToken();
  if (apiToken) {
    headers.authorization = `Bearer ${apiToken}`;
  }

  return headers;
}

function readApiToken() {
  try {
    return window.localStorage.getItem("sightline_api_token") || "";
  } catch {
    return "";
  }
}

function writeApiToken(value) {
  try {
    window.localStorage.setItem("sightline_api_token", value.trim());
  } catch {
    return;
  }
}

export default App;
