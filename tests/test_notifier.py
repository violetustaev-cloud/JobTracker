import os
import unittest
from unittest.mock import patch

import notifier


class NotifierTests(unittest.TestCase):
    def test_send_email_escapes_job_content(self):
        environment = {
            "SENDGRID_API_KEY": "test-key",
            "SENDER_EMAIL": "sender@example.com",
            "RECIPIENT_EMAIL": "recipient@example.com",
        }
        with (
            patch.dict(os.environ, environment, clear=True),
            patch.object(notifier, "Mail") as mail,
            patch.object(notifier, "SendGridAPIClient") as client,
        ):
            client.return_value.send.return_value.status_code = 202

            status = notifier.send_email([{"id": 1, "name": "<script>"}])

        self.assertEqual(status, 202)
        self.assertIn("&lt;script&gt;", mail.call_args.kwargs["html_content"])

    def test_send_email_requires_configuration(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "SENDGRID_API_KEY"):
                notifier.send_email([{"id": 1, "name": "New role"}])


if __name__ == "__main__":
    unittest.main()
