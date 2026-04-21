// We keep state in one small object first because it is easy to read and easy to replace later.
export function createInitialState() {
  return {
    sources: [
      { id: "api-demo", kind: "api", status: "waiting" },
      { id: "csv-demo", kind: "csv", status: "waiting" },
      { id: "scraper-demo", kind: "scraper", status: "waiting" },
      { id: "webhook-demo", kind: "webhook", status: "waiting" },
    ],
    entities: [
      { id: "entity-a", label: "Entity A", note: "TODO [CORE]: pick a real entity model" },
      { id: "entity-b", label: "Entity B", note: "TODO [CORE]: define investigation behaviors" },
    ],
    report: {
      title: "Report Stub",
      preview: "TODO [CORE]: generate a real report summary from investigation evidence.",
    },
  };
}

