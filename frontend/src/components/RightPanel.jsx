import { SummaryCard } from "./SummaryCard.jsx";

export function RightPanel({ graph, selectedNode, selectedEdges, resolution, records }) {
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
