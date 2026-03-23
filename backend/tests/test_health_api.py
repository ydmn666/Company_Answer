import sys
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from base import APITestCase


class HealthAPITestCase(APITestCase):
    def test_health_returns_component_snapshot(self):
        fake_snapshot = {
            "status": "ok",
            "app_env": "development",
            "components": {
                "database": {"status": "ok"},
                "redis": {"status": "disabled", "detail": "redis cache disabled"},
                "log_dir": {"status": "ok", "path": "backend/logs"},
                "document_storage": {"status": "ok", "path": "backend/data/source_files"},
            },
        }

        with patch("app.main.health_snapshot", return_value=fake_snapshot):
            response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("components", data)
        self.assertEqual(data["components"]["database"]["status"], "ok")
        self.assertEqual(data["components"]["redis"]["status"], "disabled")
