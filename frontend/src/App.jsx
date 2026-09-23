import { useEffect, useState } from "react";

import { GraphCanvas } from "./components/GraphCanvas.jsx";
import { LeftPanel } from "./components/LeftPanel.jsx";
import { RightPanel } from "./components/RightPanel.jsx";
import {
  fetchWorkspacePayload,
  readApiToken,
  rebuildGraph,
  runFullSource,
  submitSourceRaw,
  writeApiToken,
} from "./lib/api.js";
import {
  buildManualQuery,
  buildProviderQuery,
  createDefaultProviderForm,
  createEmptyManualForm,
  CSV_EXAMPLE,
} from "./lib/forms.js";
import { getProviderOption } from "./lib/providers.js";

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

export default App;
