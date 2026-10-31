import json
import unittest
from unittest.mock import patch

import main


class FakeBatchWriter:
    def __init__(self, table):
        self.table = table

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def put_item(self, Item):
        self.table.items[Item["job_id"]] = Item


class FakeTable:
    def __init__(self, job_ids=()):
        self.items = {job_id: {"job_id": job_id} for job_id in job_ids}

    def get_item(self, Key, ConsistentRead):
        item = self.items.get(Key["job_id"])
        return {"Item": item} if item else {}

    def batch_writer(self):
        return FakeBatchWriter(self)


class MainTests(unittest.TestCase):
    def test_find_new_jobs_filters_seen_and_duplicate_ids(self):
        jobs = [
            {"id": 1, "name": "Already seen"},
            {"id": 2, "name": "New role"},
            {"id": 2, "name": "Duplicate role"},
            {"name": "Missing ID"},
        ]

        with self.assertLogs(main.logger, level="WARNING"):
            result = main.find_new_jobs(jobs, {"1"})

        self.assertEqual(result, [{"id": 2, "name": "New role"}])

    def test_lambda_handler_emails_new_jobs_then_records_ids(self):
        jobs = [{"id": 1, "name": "Already seen"}, {"id": 2, "name": "New role"}]
        table = FakeTable(["1"])

        with (
            patch.object(main, "_dynamodb_table", return_value=table),
            patch.object(main, "fetch_jobs", return_value=jobs),
            patch.object(main, "send_email", return_value=202) as send_email,
        ):
            result = main.handler({}, None)

        send_email.assert_called_once_with([jobs[1]])
        self.assertEqual(table.items.keys(), {"1", "2"})
        self.assertEqual(json.loads(result["body"])["new_jobs"], 1)

    def test_lambda_handler_does_not_record_jobs_when_email_fails(self):
        jobs = [{"id": 2, "name": "New role"}]
        table = FakeTable()

        with (
            patch.object(main, "_dynamodb_table", return_value=table),
            patch.object(main, "fetch_jobs", return_value=jobs),
            patch.object(main, "send_email", side_effect=RuntimeError("email failed")),
        ):
            with self.assertRaisesRegex(RuntimeError, "email failed"):
                main.handler({}, None)

        self.assertEqual(table.items, {})


if __name__ == "__main__":
    unittest.main()
