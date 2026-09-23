export const PROVIDER_OPTIONS = [
  { provider: "ipinfo", sourceKind: "api", label: "IPinfo", placeholder: "8.8.8.8" },
  { provider: "crt.sh", sourceKind: "scraper", label: "crt.sh", placeholder: "example.com" },
  { provider: "nominatim", sourceKind: "api", label: "Nominatim", placeholder: "Indianapolis" },
  { provider: "opensky", sourceKind: "api", label: "OpenSky", placeholder: "AAL123" },
];

export function getProviderOption(provider) {
  return PROVIDER_OPTIONS.find((option) => option.provider === provider) || PROVIDER_OPTIONS[0];
}
