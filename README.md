# Internship Job Notifier

I build this project to find software jobs from specific companies.
The API I used is with Nvidia's Carrer Page.

The default search looks for Deep Learning Software internships. You can point
it at a different search by setting `JOBS_URL`.

The NVIDIA careers URL used here is an endpoint from their website, not a
documented public API. It could change or stop working, so check the site's
terms before using it. This is a personal project and isn't affiliated with or
endorsed by NVIDIA.

## Running locally

You'll need Python 3.10 or newer and a SendGrid account with a verified sender
address. Create a virtual environment and install the dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Make sure to reset these values to your own details, these commands are for a local PowerShell session.

```powershell
$env:SENDGRID_API_KEY = "your-sendgrid-api-key"
$env:SENDER_EMAIL = "verified-sender@example.com"
$env:RECIPIENT_EMAIL = "you@example.com"
python main.py
```

To use a different job search, set `JOBS_URL`:

```powershell
$env:JOBS_URL = "https://example.com/your-search-endpoint"
```

The program saves notified job IDs in `seen_jobs.json` so it won't email the
same listings again. That file is excluded from Git. On its first run, it
treats all matching listings as new.

The current code includes a Lambda handler. In this version, DynamoDB stores
the job IDs that have already been emailed.

1. Create a DynamoDB table with a string partition key named `job_id`.
2. Create a Lambda function using Python 3.10 or newer and set the handler to
   `main.handler`.
3. Add these environment variables to the function:
   - `SENDGRID_API_KEY`: SendGrid API key
   - `SENDER_EMAIL`: sender address verified with SendGrid
   - `RECIPIENT_EMAIL`: destination for notifications
   - `SEEN_JOBS_TABLE`: name of the DynamoDB table
   - `JOBS_URL` (optional): alternate jobs search endpoint
4. Give the Lambda execution role permission to read and write items in the
   table (`dynamodb:GetItem` and `dynamodb:BatchWriteItem`).
5. Include the packages in `requirements.txt` in the deployment or a Lambda
   layer.
6. If you want it to run regularly, create an EventBridge schedule to invoke
   the function.

On the first run, every matching listing is considered new. If you don't want
an email with all the current results, add those job IDs to the table before
enabling the schedule.

## Tests

Run the unit tests from the project folder:

```powershell
python -m unittest discover -s tests -v
```

The tests use mocks, so they don't send email or make AWS requests.

## Before publishing

Keep your SendGrid API key and other credentials out of GitHub. The values in
the examples above are placeholders. Use your real settings only in your local
environment or AWS Lambda configuration.