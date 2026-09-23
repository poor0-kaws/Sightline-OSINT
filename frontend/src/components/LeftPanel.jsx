import { getProviderOption, PROVIDER_OPTIONS } from "../lib/providers.js";
import { SummaryCard } from "./SummaryCard.jsx";

export function LeftPanel({
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
