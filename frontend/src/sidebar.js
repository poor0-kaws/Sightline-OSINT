// We keep sidebar rendering separate so source lists and annotations can grow independently.
export function renderSidebar(rootElement, state) {
  rootElement.innerHTML = `
    <div class="stack">
      <div class="sidebar-card">
        <strong>Sources</strong>
        <p class="muted">Where ingestion jobs will come from.</p>
      </div>
      ${state.sources
        .map(
          (source) => `
            <div class="sidebar-card">
              <strong>${source.id}</strong>
              <p class="muted">kind: ${source.kind}</p>
              <p class="muted">status: ${source.status}</p>
            </div>
          `,
        )
        .join("")}
      <div class="sidebar-card">
        <strong>Annotations</strong>
        <p class="muted">TODO [OPTIONAL]: show analyst notes and link evidence here.</p>
      </div>
    </div>
  `;
}

