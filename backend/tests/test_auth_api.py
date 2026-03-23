import sys
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.schemas.auth import LoginResponse, UserInfo

from base import APITestCase


class AuthAPITestCase(APITestCase):
    def test_login_success_returns_token_and_user(self):
        with patch("app.api.routes.auth.login_user") as login_user:
            login_user.return_value = LoginResponse(
                token="mock-token",
                user=UserInfo(id="admin-1", username="admin", name="System Admin", role="admin"),
            )

            response = self.client.post(
                "/api/auth/login",
                json={"username": "admin", "password": "password"},
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["token"], "mock-token")
        self.assertEqual(data["user"]["username"], "admin")
        self.assertEqual(data["user"]["role"], "admin")

    def test_login_invalid_credentials_returns_401(self):
        with patch("app.api.routes.auth.login_user") as login_user:
            login_user.side_effect = ValueError("Invalid username or password")

            response = self.client.post(
                "/api/auth/login",
                json={"username": "admin", "password": "wrong"},
            )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Invalid username or password")

    def test_me_returns_current_user_profile(self):
        response = self.client.get("/api/auth/me", headers={"Authorization": "Bearer mock-token"})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["username"], "employee")
        self.assertEqual(data["role"], "employee")
