import { getConfidenceClass } from "../lib/graph.js";

export function GraphCanvas({ graph, selectedNodeId, onSelectNode, isPulsing }) {
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
