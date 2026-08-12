import json
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path

from app.server import create_server


ROOT = Path(__file__).resolve().parents[1]


class WorkbenchApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server("127.0.0.1", 0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_port

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def get_json(self, path):
        connection = HTTPConnection("127.0.0.1", self.port)
        connection.request("GET", path)
        response = connection.getresponse()
        data = json.loads(response.read().decode("utf-8"))
        connection.close()
        return response.status, data

    def test_health_uses_cutaihub_defaults_without_exposing_key(self):
        status, data = self.get_json("/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(data["base_url"], "https://api.cutaihub.com/v1")
        self.assertEqual(data["model"], "gpt5.6")
        self.assertNotIn("api_key", data)

    def test_catalog_and_home_page_are_available(self):
        status, data = self.get_json("/api/catalog/themes")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(data["themes"]), 3)

        connection = HTTPConnection("127.0.0.1", self.port)
        connection.request("GET", "/")
        response = connection.getresponse()
        body = response.read().decode("utf-8")
        connection.close()
        self.assertEqual(response.status, 200)
        self.assertIn("PPT Agent", body)


if __name__ == "__main__":
    unittest.main()
