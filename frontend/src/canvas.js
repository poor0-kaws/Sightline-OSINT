// We keep canvas rendering in one module so UI behavior can evolve without touching app startup.
export function renderCanvas(rootElement, state) {
  rootElement.innerHTML = "";

  const diagram = document.createElement("div");
  diagram.className = "canvas-diagram";

  const leftCard = document.createElement("div");
  leftCard.className = "entity-card";
  leftCard.innerHTML = `
    <strong>${state.entities[0].label}</strong>
    <p class="muted">${state.entities[0].note}</p>
  `;

  const linkLabel = document.createElement("div");
  linkLabel.className = "link-label";
  linkLabel.textContent = "Link Stub";

  const rightCard = document.createElement("div");
  rightCard.className = "entity-card";
  rightCard.innerHTML = `
    <strong>${state.entities[1].label}</strong>
    <p class="muted">${state.entities[1].note}</p>
  `;

  // TODO [CORE]: replace this static preview with a real draggable and linkable canvas.
  diagram.append(leftCard, linkLabel, rightCard);
  rootElement.append(diagram);
}

