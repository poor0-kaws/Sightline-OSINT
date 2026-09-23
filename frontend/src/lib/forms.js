export const CSV_EXAMPLE = JSON.stringify(
  [
    {
      full_name: "Maya Patel",
      email: "maya.patel@gmail.com",
      phone: "3175550101",
      company_name: "OpenAI LLC",
    },
  ],
  null,
  2,
);

export function createEmptyManualForm() {
  return {
    note: "",
    full_name: "",
    email: "",
    phone: "",
    company_name: "",
  };
}

export function createDefaultProviderForm() {
  return {
    provider: "ipinfo",
    queryText: "8.8.8.8",
  };
}

export function buildManualQuery(form) {
  const query = {};

  for (const [key, value] of Object.entries(form)) {
    const cleanedValue = value.trim();
    if (!cleanedValue) {
      continue;
    }

    query[key] = cleanedValue;
  }

  return query;
}

export function buildProviderQuery(queryText) {
  const cleanedValue = queryText.trim();
  if (!cleanedValue) {
    throw new Error("Provider query is required.");
  }

  if (cleanedValue.startsWith("{") || cleanedValue.startsWith("[")) {
    return JSON.parse(cleanedValue);
  }

  return cleanedValue;
}
