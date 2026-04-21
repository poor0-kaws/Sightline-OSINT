// We keep report rendering in one place so export options can be added later without touching other UI code.
export function renderReport(rootElement, state) {
  rootElement.innerHTML = `
    <div class="report-card">
      <strong>${state.report.title}</strong>
      <p class="muted">${state.report.preview}</p>
      <p class="muted">TODO [CORE]: choose report sections, evidence layout, and export actions.</p>
    </div>
  `;
}

