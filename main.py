"""Simple entrypoint for the scaffold."""

# `configure_logging` sets up a readable logger for the demo runner.
from backend.logging_config import configure_logging
# `render_skeleton_dashboard` prints an immediate visual stub so the project feels alive.
from backend.utils.visualization import render_skeleton_dashboard


def main() -> None:
    """Run the no-dependencies-needed scaffold preview."""
    configure_logging()
    print("skeleton ready")
    render_skeleton_dashboard()


if __name__ == "__main__":
    main()

