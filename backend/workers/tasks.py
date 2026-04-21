"""Background task shells."""

# `celery_app` is the shared Celery application object.
from backend.workers.celery_app import celery_app


@celery_app.task(name="ingestion.run")
def run_ingestion_job(job_id: str) -> dict:
    """Background task shell for ingestion."""
    _ = job_id
    # TODO [OPTIONAL]: load the job, run the connector, and persist normalized records.
    return {"status": "stub", "task": "ingestion.run"}


@celery_app.task(name="reports.build")
def build_report(report_id: str) -> dict:
    """Background task shell for report generation."""
    _ = report_id
    # TODO [OPTIONAL]: assemble evidence and render the final report artifact.
    return {"status": "stub", "task": "reports.build"}

