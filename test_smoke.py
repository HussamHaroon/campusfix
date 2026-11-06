"""Smoke tests for CampusFix (run with: python -m unittest test_smoke).

Covers the critical flows used in the Lab 16 test plan: login
(positive/negative), request submission (positive/negative), and the
role-based access check. Uses a temporary SQLite file so every request
sees the same seeded data.
"""
import os
import sqlite3
import tempfile
import unittest

import app as campusfix


class CampusFixSmokeTests(unittest.TestCase):
    def setUp(self):
        fd, self.dbpath = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        campusfix.DB = self.dbpath
        d = sqlite3.connect(self.dbpath)
        d.executescript(campusfix.SCHEMA)
        d.execute("INSERT INTO category(name) VALUES('Electrical')")
        d.execute("INSERT INTO user(name,email,password,role) "
                  "VALUES('Ali Raza','ali@test.pk','ali123','student')")
        d.execute("INSERT INTO user(name,email,password,role) "
                  "VALUES('Staff','staff@test.pk','staff123','staff')")
        d.commit()
        d.close()
        self.client = campusfix.app.test_client()

    def tearDown(self):
        os.remove(self.dbpath)

    def login(self, email, pw):
        return self.client.post("/login", data={"email": email, "password": pw},
                                follow_redirects=True)

    def test_health(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)

    def test_login_valid(self):
        r = self.login("ali@test.pk", "ali123")
        self.assertIn(b"Submit new request", r.data)

    def test_login_invalid(self):
        r = self.login("ali@test.pk", "wrong")
        self.assertIn(b"Invalid email or password.", r.data)

    def test_submit_request_valid(self):
        self.login("ali@test.pk", "ali123")
        r = self.client.post("/submit", data={
            "title": "Broken fan", "category": "1", "location": "Hostel B-12",
            "description": "Ceiling fan not working", "priority": "high",
        }, follow_redirects=True)
        self.assertIn(b"created successfully", r.data)

    def test_submit_request_empty_field(self):
        self.login("ali@test.pk", "ali123")
        r = self.client.post("/submit", data={
            "title": "", "category": "1", "location": "Hostel B-12",
            "description": "", "priority": "low",
        }, follow_redirects=True)
        self.assertIn(b"All fields are required.", r.data)

    def test_student_cannot_open_staff_queue(self):
        self.login("ali@test.pk", "ali123")
        r = self.client.get("/queue", follow_redirects=True)
        self.assertIn(b"Staff access only.", r.data)


if __name__ == "__main__":
    unittest.main()
