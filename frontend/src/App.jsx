import { useEffect, useState } from "react";

function App() {
  const [graph, setGraph] = useState(null);
  const [selectedNodeId, setSelectedNodeId] = useState("");
  const [isPulsing, setIsPulsing] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    let isMounted = true;

    async function loadGraph() {
      try {
        const response = await fetch("/app/graph-data");
        if (!response.ok) {
          throw new Error(`Graph data request failed with status ${response.status}.`);
        }

        const payload = await response.json();
        if (!isMounted) {
          return;
        }

        setGraph(payload);
        setSelectedNodeId(payload.nodes[0]?.id || "");
      } catch (error) {
        if (!isMounted) {
          return;
        }

        setErrorMessage(String(error));
      }
    }

    loadGraph();

    return () => {
      isMounted = false;
    };
  }, []);

  let selectedNode = null;
  if (graph && selectedNodeId) {
    selectedNode = graph.nodes.find((node) => node.id === selectedNodeId) || null;
  }

  let selectedEdges = [];
  if (graph && selectedNode) {
    selectedEdges = graph.edges.filter((edge) => edge.from === selectedNode.id || edge.to === selectedNode.id);
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
      <LeftPanel graph={graph} />
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
      <RightPanel graph={graph} selectedNode={selectedNode} selectedEdges={selectedEdges} />
    </div>
  );
}

function LeftPanel({ graph }) {
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

function RightPanel({ graph, selectedNode, selectedEdges }) {
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

export default App;
