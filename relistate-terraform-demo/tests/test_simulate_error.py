"""Run with: python -m unittest discover -s tests -v (requires Flask)."""
import importlib.util
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock


class SimulateErrorReportingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.old_database_path = os.environ.get("DATABASE_PATH")
        os.environ["DATABASE_PATH"] = str(pathlib.Path(cls.tmp.name) / "test.sqlite3")
        path = pathlib.Path(__file__).parents[1] / "app" / "app.py"
        spec = importlib.util.spec_from_file_location("relistate_test_app", path)
        cls.module = importlib.util.module_from_spec(spec)
        # Register before executing so Flask resolves templates/ relative to app/, not the working directory.
        sys.modules[spec.name] = cls.module
        spec.loader.exec_module(cls.module)
        cls.client = cls.module.app.test_client()

    @classmethod
    def tearDownClass(cls):
        if cls.old_database_path is None:
            os.environ.pop("DATABASE_PATH", None)
        else:
            os.environ["DATABASE_PATH"] = cls.old_database_path
        cls.tmp.cleanup()

    def test_simulated_failure_reports_error_to_new_relic(self):
        fake_agent = mock.Mock()
        with mock.patch.object(self.module, "nr_agent", fake_agent):
            response = self.client.get("/simulate/error?rate=1")
        self.assertIn(response.status_code, (500, 503))
        self.assertEqual(response.json, {"status": "error", "message": "Simulated server failure"})
        fake_agent.notice_error.assert_called_once()
        kwargs = fake_agent.notice_error.call_args.kwargs
        exc_type, exc_value, exc_traceback = kwargs["error"]
        self.assertIs(exc_type, self.module.SimulatedServerFailure)
        self.assertIsNotNone(exc_traceback)
        self.assertEqual(kwargs["status_code"], response.status_code)
        self.assertEqual(kwargs["attributes"]["demo.http_status_code"], response.status_code)

    def test_no_error_reported_when_rate_is_zero(self):
        fake_agent = mock.Mock()
        with mock.patch.object(self.module, "nr_agent", fake_agent):
            response = self.client.get("/simulate/error?rate=0")
        self.assertEqual(response.status_code, 200)
        fake_agent.notice_error.assert_not_called()


if __name__ == "__main__":
    unittest.main()
