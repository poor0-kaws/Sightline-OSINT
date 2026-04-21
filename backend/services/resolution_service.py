"""Service layer for entity resolution."""

# `EntityLinkSuggestion` is the shape of a possible match between entities.
from backend.schemas.entity import EntityLinkSuggestion
# `EntityRecord` is the normalized entity input shape.
from backend.schemas.entity import EntityRecord
# `Dedupe` is the planned matching library.
from backend.utils.optional_deps import Dedupe


# We use a service class because entity resolution usually grows stateful and complex quickly.
class ResolutionService:
    """Shell for entity matching and deduplication."""

    def __init__(self) -> None:
        self.matcher = Dedupe()

    def score_candidate_matches(self, entities: list[EntityRecord]) -> list[EntityLinkSuggestion]:
        """Return potential matches between entities."""
        _ = entities
        # TODO [CORE]: choose features, scoring, thresholds, and review workflow.
        return []

    def resolve_entities(self, entities: list[EntityRecord]) -> list[EntityRecord]:
        """Return the surviving merged entities."""
        _ = entities
        # TODO [CORE]: decide when entities should merge and how conflicts are handled.
        return []

