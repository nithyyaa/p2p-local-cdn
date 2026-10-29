
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.origin import create_origin_app


class TestOriginServer(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.root = Path(self.temp_dir.name)
        (self.root / "hello.txt").write_bytes(b"Hello from origin!")
        (self.root / "data.bin").write_bytes(b"\x00\x01\x02\x03")

        self.client = TestClient(create_origin_app(self.root))

    def test_health_endpoint(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_serve_existing_file(self):
        response = self.client.get("/files/hello.txt")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"Hello from origin!")

    def test_missing_file_returns_404(self):
        response = self.client.get("/files/missing.txt")

        self.assertEqual(response.status_code, 404)

    def test_reject_path_traversal(self):
        response = self.client.get("/files/..%5Csecret.txt")

        self.assertIn(response.status_code, (400, 404))

    def test_reject_directory(self):
        response = self.client.get("/files/subfolder")

        self.assertEqual(response.status_code, 404)

    def test_catalogue_lists_available_files(self):
        response = self.client.get("/files")

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("files", data)

        file_names = [item["file_name"] for item in data["files"]]

        self.assertIn("hello.txt", file_names)
        self.assertIn("data.bin", file_names)

    def test_catalogue_reports_file_sizes(self):
        response = self.client.get("/files")

        self.assertEqual(response.status_code, 200)

        files_by_name = {
            item["file_name"]: item
            for item in response.json()["files"]
        }

        self.assertEqual(
    files_by_name["hello.txt"]["size_bytes"],
    len(b"Hello from origin!"),
)

    def test_stats_endpoint(self):
        response = self.client.get("/stats")

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("successful_requests", data)
        self.assertIn("bytes_served", data)


if __name__ == "__main__":
    unittest.main()
