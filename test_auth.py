import unittest
from dashboard_server import app, DASHBOARD_AUTH_KEY


class TestAuth(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        app.config["TESTING"] = True

    def test_no_auth(self):
        response = self.app.get("/api/health")
        self.assertEqual(response.status_code, 200)

        response = self.app.get("/api/state")
        if DASHBOARD_AUTH_KEY:
            self.assertEqual(response.status_code, 401)
        else:
            self.assertEqual(response.status_code, 200)

    def test_bearer_token(self):
        if not DASHBOARD_AUTH_KEY:
            return
        headers = {"Authorization": f"Bearer {DASHBOARD_AUTH_KEY}"}
        response = self.app.get("/api/state", headers=headers)
        self.assertEqual(response.status_code, 200)

        headers = {"Authorization": f"Bearer invalid"}
        response = self.app.get("/api/state", headers=headers)
        self.assertEqual(response.status_code, 401)

    def test_query_param(self):
        if not DASHBOARD_AUTH_KEY:
            return
        response = self.app.get(f"/api/state?auth_key={DASHBOARD_AUTH_KEY}")
        self.assertEqual(response.status_code, 200)

        response = self.app.get(f"/api/state?auth_key=invalid")
        self.assertEqual(response.status_code, 401)

    def test_cookie(self):
        if not DASHBOARD_AUTH_KEY:
            return
        self.app.set_cookie("dashboard_auth", DASHBOARD_AUTH_KEY)
        response = self.app.get("/api/state")
        self.assertEqual(response.status_code, 200)

        self.app.delete_cookie("dashboard_auth")
        self.app.set_cookie("dashboard_auth", "invalid")
        response = self.app.get("/api/state")
        self.assertEqual(response.status_code, 401)

    def test_login(self):
        if not DASHBOARD_AUTH_KEY:
            return
        response = self.app.post("/api/login", json={"key": DASHBOARD_AUTH_KEY})
        self.assertEqual(response.status_code, 200)

        response = self.app.post("/api/login", json={"key": "invalid"})
        self.assertEqual(response.status_code, 401)

    def test_login_invalid_type(self):
        if not DASHBOARD_AUTH_KEY:
            return
        response = self.app.post("/api/login", json={"key": 123})
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
