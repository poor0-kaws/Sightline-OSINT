export function getConfidenceClass(confidence) {
  if (confidence >= 90) {
    return "edge-high";
  }

  if (confidence >= 70) {
    return "edge-medium";
  }

  return "edge-low";
}
