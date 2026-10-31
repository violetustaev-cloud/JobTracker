import json
import logging
import os
from pathlib import Path
from typing import Any

import requests

from notifier import send_email


logger = logging.getLogger(__name__)
DEFAULT_JOBS_URL = (
    "https://jobs.nvidia.com/api/pcsx/search?domain=nvidia.com"
    "&query=Deep%20Learning%20Software&location=&start=0&sort_by=relevance"
    "&filter_job_type=intern+%28fixed+term%29&filter_hiring_title=Software"
)
SEEN_JOBS_FILE = Path(__file__).with_name("seen_jobs.json")


def load_seen_jobs() -> set[str]:
    """Load job IDs previously recorded by a local run."""
    try:
        with SEEN_JOBS_FILE.open(encoding="utf-8") as file:
            return {str(job_id) for job_id in json.load(file)}
    except FileNotFoundError:
        return set()


def save_seen_jobs(job_ids: set[str]) -> None:
    """Save job IDs for subsequent local runs."""
    with SEEN_JOBS_FILE.open("w", encoding="utf-8") as file:
        json.dump(sorted(job_ids), file, indent=2)


def fetch_jobs(url: str | None = None) -> list[dict[str, Any]]:
    """Fetch internship listings from the NVIDIA jobs endpoint."""
    response = requests.get(
        url or os.environ.get("JOBS_URL", DEFAULT_JOBS_URL),
        headers={"User-Agent": "StudentProjectBot/1.0"},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()

    if not isinstance(payload, dict):
        raise ValueError("The jobs API response must be a JSON object.")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise ValueError("The jobs API response is missing its 'data' object.")
    jobs = data.get("positions")
    if not isinstance(jobs, list):
        raise ValueError("The jobs API response is missing its 'positions' list.")
    if not all(isinstance(job, dict) for job in jobs):
        raise ValueError("The jobs API response contains an invalid job listing.")
    return jobs


def find_new_jobs(
    jobs: list[dict[str, Any]], seen_ids: set[str]
) -> list[dict[str, Any]]:
    """Return unique jobs with IDs that have not been seen before."""
    new_jobs = []
    checked_ids = set(seen_ids)
    for job in jobs:
        job_id = job.get("id")
        if job_id is None:
            logger.warning("Skipping a job listing without an ID: %r", job)
            continue
        normalized_id = str(job_id)
        if normalized_id not in checked_ids:
            new_jobs.append(job)
            checked_ids.add(normalized_id)
    return new_jobs


def _dynamodb_table():
    table_name = os.environ.get("SEEN_JOBS_TABLE")
    if not table_name:
        raise RuntimeError("SEEN_JOBS_TABLE must be set when running in Lambda.")

    import boto3

    return boto3.resource("dynamodb").Table(table_name)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda entry point. The DynamoDB table must use job_id as its key."""
    del event, context
    table = _dynamodb_table()
    jobs = fetch_jobs()

    job_ids = {
        str(job["id"])
        for job in jobs
        if isinstance(job, dict) and job.get("id") is not None
    }
    seen_ids = set()
    for job_id in job_ids:
        result = table.get_item(
            Key={"job_id": job_id},
            ConsistentRead=True,
        )
        if "Item" in result:
            seen_ids.add(job_id)

    new_jobs = find_new_jobs(jobs, seen_ids)
    if not new_jobs:
        logger.info("No new internships found.")
        return {"statusCode": 200, "body": json.dumps({"new_jobs": 0})}

    status_code = send_email(new_jobs)
    with table.batch_writer() as batch:
        for job in new_jobs:
            batch.put_item(Item={"job_id": str(job["id"])})

    logger.info("Sent an email for %d new internships.", len(new_jobs))
    return {
        "statusCode": 200,
        "body": json.dumps(
            {"new_jobs": len(new_jobs), "email_status": status_code}
        ),
    }


def run_locally() -> None:
    """Run the checker locally using seen_jobs.json for state."""
    seen_ids = load_seen_jobs()
    new_jobs = find_new_jobs(fetch_jobs(), seen_ids)
    if not new_jobs:
        logger.info("No new internships found.")
        return

    status_code = send_email(new_jobs)
    seen_ids.update(str(job["id"]) for job in new_jobs)
    save_seen_jobs(seen_ids)
    logger.info(
        "Email notification status: %d. Saved %d new job IDs.",
        status_code,
        len(new_jobs),
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_locally()
