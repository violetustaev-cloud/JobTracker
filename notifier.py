import html
import os
from typing import Any

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


def send_email(new_jobs: list[dict[str, Any]]) -> int:
    api_key = os.environ.get("SENDGRID_API_KEY")
    from_email = os.environ.get("SENDER_EMAIL")
    to_email = os.environ.get("RECIPIENT_EMAIL")
    missing_settings = [
        name
        for name, value in (
            ("SENDGRID_API_KEY", api_key),
            ("SENDER_EMAIL", from_email),
            ("RECIPIENT_EMAIL", to_email),
        )
        if not value
    ]
    if missing_settings:
        raise RuntimeError(
            "Missing required email configuration: " + ", ".join(missing_settings)
        )

    job_items = "".join(
        f"<li>{html.escape(str(job.get('name', 'Untitled job')))} "
        f"(ID: {html.escape(str(job.get('id', 'unknown')))})</li>"
        for job in new_jobs
    )
    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject="New NVIDIA Internships Found",
        html_content=f"<p>New NVIDIA Internships Found:</p><ul>{job_items}</ul>",
    )

    response = SendGridAPIClient(api_key).send(message)
    if not 200 <= response.status_code < 300:
        raise RuntimeError(
            f"SendGrid returned an unsuccessful status: {response.status_code}"
        )
    return response.status_code
