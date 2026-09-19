import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import lms_api
import scanner_api


class LmsApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = lms_api.LmsStore(Path(self.temp_dir.name) / "lms-test.db")
        self.store_patch = patch.object(lms_api, "STORE", self.store)
        self.store_patch.start()
        self.client = TestClient(scanner_api.app)

    def tearDown(self) -> None:
        self.client.close()
        self.store_patch.stop()
        self.temp_dir.cleanup()

    def test_curriculum_has_all_six_levels_and_expected_lesson_counts(self) -> None:
        response = self.client.get("/api/curriculum")

        self.assertEqual(200, response.status_code)
        levels = response.json()["levels"]
        self.assertEqual([1, 2, 3, 4, 5, 6], [level["level"] for level in levels])
        self.assertEqual([1, 26, 6, 10, 11, 3], [len(level["lessons"]) for level in levels])
        self.assertEqual("level-1-dot-explorer", levels[0]["lessons"][0]["id"])
        self.assertEqual("level-6-scan-own-page", levels[5]["lessons"][2]["id"])

    def test_progress_scores_streak_and_student_analytics_round_trip(self) -> None:
        progress = self.client.post("/api/progress", json={
            "userId": "student-1", "lessonId": "level-2-a", "level": 2,
            "status": "COMPLETED", "score": 100, "accuracy": 1.0,
            "completedAt": 1_800_000_000_000,
        })
        score = self.client.post("/api/scores", json={
            "id": "score-1", "userId": "student-1", "lessonId": "level-2-a",
            "questionId": "letter-a", "userAnswer": "A", "correctAnswer": "A",
            "isCorrect": True, "timestamp": 1_800_000_000_000,
        })
        streak = self.client.post("/api/streaks", json={
            "userId": "student-1", "currentStreak": 2, "longestStreak": 4,
            "lastActiveDate": "2026-09-18",
        })
        stored = self.client.get("/api/progress/student-1")
        analytics = self.client.get("/api/analytics/student/student-1")

        self.assertEqual(200, progress.status_code)
        self.assertEqual(200, score.status_code)
        self.assertEqual(200, streak.status_code)
        self.assertEqual("COMPLETED", stored.json()["progress"][0]["status"])
        self.assertEqual(1, analytics.json()["totalLessonsCompleted"])
        self.assertEqual(1.0, analytics.json()["accuracyByLetter"]["A"])
        self.assertEqual(4, analytics.json()["streak"]["longestStreak"])

    def test_validation_rejects_bad_progress_and_bad_curriculum_level(self) -> None:
        bad_progress = self.client.post("/api/progress", json={
            "userId": "student-1", "lessonId": "bad", "level": 9,
            "status": "COMPLETED", "score": -1, "accuracy": 2.0,
        })
        missing_level = self.client.get("/api/curriculum/9")

        self.assertEqual(422, bad_progress.status_code)
        self.assertEqual(404, missing_level.status_code)

    def test_school_class_analytics_and_csv_exports(self) -> None:
        requests = [
            ("/api/admin/schools", {"id": "school-1", "name": "Demo School", "district": "D", "state": "S"}),
            ("/api/admin/teachers", {"id": "teacher-1", "schoolId": "school-1", "name": "Teacher", "email": "teacher@example.com", "role": "TEACHER"}),
            ("/api/admin/classes", {"id": "class-1", "schoolId": "school-1", "teacherId": "teacher-1", "name": "Class One"}),
            ("/api/admin/students", {"id": "student-1", "schoolId": "school-1", "classId": "class-1", "name": "Student", "grade": "5", "accessibilityNeeds": ""}),
        ]
        for path, payload in requests:
            response = self.client.post(path, json=payload)
            self.assertEqual(201, response.status_code, response.text)
        self.client.post("/api/progress", json={
            "userId": "student-1", "lessonId": "level-1-1", "level": 1,
            "status": "COMPLETED", "score": 100, "accuracy": 1.0,
            "completedAt": 1_800_000_000_000,
        })

        analytics = self.client.get("/api/analytics/class/class-1")
        class_csv = self.client.get("/api/reports/classes/class-1/export.csv")
        student_csv = self.client.get("/api/reports/students/student-1/export.csv")
        curriculum_csv = self.client.get("/api/reports/classes/class-1/curriculum/export.csv")

        self.assertEqual(1, analytics.json()["studentCount"])
        self.assertIn("studentId", class_csv.text)
        self.assertIn("Student", student_csv.text)
        self.assertIn("level", curriculum_csv.text)

    def test_missing_class_and_student_return_not_found(self) -> None:
        self.assertEqual(404, self.client.get("/api/analytics/class/missing").status_code)
        self.assertEqual(404, self.client.get("/api/reports/students/missing").status_code)


if __name__ == "__main__":
    unittest.main()
