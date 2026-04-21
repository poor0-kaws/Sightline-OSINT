"""Simple visible output so the skeleton shows life immediately."""

# `datetime` lets us stamp the dashboard with the current moment.
from datetime import datetime


def _render_pipeline_rows() -> list[str]:
    """Build simple status rows for the fake pipeline preview."""
    stages = [
        ("API pull", "waiting", "TODO [CORE]: fetch and normalize remote API data"),
        ("CSV import", "waiting", "TODO [CORE]: map columns into shared entity fields"),
        ("Scraper run", "waiting", "TODO [CORE]: extract structured signals from HTML"),
        ("Webhook intake", "waiting", "TODO [CORE]: validate and normalize live events"),
        ("Entity resolve", "waiting", "TODO [CORE]: score and merge duplicate entities"),
        ("Graph write", "waiting", "TODO [CORE]: store nodes and links in Neo4j"),
        ("Report build", "waiting", "TODO [CORE]: turn evidence into an investigation report"),
    ]
    return [f"[{status:^7}] {name:<14} -> {note}" for name, status, note in stages]


def _render_canvas_preview() -> str:
    """Return a tiny ASCII sketch of the future investigation canvas."""
    return "\n".join(
        [
            "Canvas preview",
            "+----------------------+     +----------------------+",
            "| Entity A             |-----| Entity B             |",
            "| TODO: person/org     |     | TODO: account/domain |",
            "+----------------------+     +----------------------+",
            "           \\                         /",
            "            \\------[ annotation ]---/",
        ]
    )


def render_skeleton_dashboard() -> None:
    """Print a readable dashboard for the scaffold."""
    print("")
    print(f"Scaffold snapshot at {datetime.now().isoformat(timespec='seconds')}")
    print("")
    print("Pipeline preview")
    for row in _render_pipeline_rows():
        print(row)
    print("")
    print(_render_canvas_preview())
    print("")
    print("Next useful command: python -m pytest")

