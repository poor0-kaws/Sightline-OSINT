// `fetchDashboardData` is where real backend communication will live later.
import { fetchDashboardData } from "./api.js";
// `renderCanvas` draws the center investigation workspace.
import { renderCanvas } from "./canvas.js";
// `renderReport` draws the right-side report preview.
import { renderReport } from "./reports.js";
// `renderSidebar` draws the left-side source and note panel.
import { renderSidebar } from "./sidebar.js";
// `createInitialState` gives us predictable stub data on first load.
import { createInitialState } from "./state.js";

const sidebarRoot = document.querySelector("#sidebar-panel");
const canvasRoot = document.querySelector("#canvas-root");
const reportRoot = document.querySelector("#report-root");
const refreshButton = document.querySelector("#refresh-button");

async function renderApp() {
  const state = createInitialState();
  const dashboardData = await fetchDashboardData();

  if (dashboardData.status !== "stub") {
    // TODO [OPTIONAL]: merge real backend data into UI state here.
  }

  renderSidebar(sidebarRoot, state);
  renderCanvas(canvasRoot, state);
  renderReport(reportRoot, state);
}

refreshButton.addEventListener("click", () => {
  renderApp();
});

renderApp();

