"""Local persistence and API contracts for optional Sciobraille LMS cloud sync.

Authentication is intentionally not faked here. Deployments must put these endpoints behind
real user authentication before exposing them outside a trusted environment.
"""

from __future__ import annotations

import os
import csv
import io
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, validator


SyncStatus = Literal["NOT_SYNCED", "SYNCING", "SYNCED", "FAILED"]
LessonStatus = Literal["NOT_STARTED", "IN_PROGRESS", "COMPLETED"]
router = APIRouter(prefix="/api", tags=["LMS"])


class ApiModel(BaseModel):
    pass


class LessonPayload(ApiModel):
    id: str
    title: str
    description: str
    order_index: int = Field(alias="orderIndex", ge=0)
    is_premium: bool = Field(alias="isPremium", default=False)


class ProgressPayload(ApiModel):
    user_id: Annotated[str, Field(alias="userId", min_length=1, max_length=128)]
    lesson_id: Annotated[str, Field(alias="lessonId", min_length=1, max_length=128)]
    level: int = Field(ge=1, le=6)
    status: LessonStatus
    score: int = Field(ge=0, le=10000)
    accuracy: float = Field(ge=0.0, le=1.0)
    completed_at: int | None = Field(alias="completedAt", default=None, ge=0)


class ScorePayload(ApiModel):
    id: Annotated[str, Field(min_length=1, max_length=128)]
    user_id: Annotated[str, Field(alias="userId", min_length=1, max_length=128)]
    lesson_id: Annotated[str, Field(alias="lessonId", min_length=1, max_length=128)]
    question_id: Annotated[str, Field(alias="questionId", min_length=1, max_length=128)]
    user_answer: str = Field(alias="userAnswer", max_length=512)
    correct_answer: str = Field(alias="correctAnswer", max_length=512)
    is_correct: bool = Field(alias="isCorrect")
    timestamp: int = Field(ge=0)


class StreakPayload(ApiModel):
    user_id: Annotated[str, Field(alias="userId", min_length=1, max_length=128)]
    current_streak: int = Field(alias="currentStreak", ge=0)
    longest_streak: int = Field(alias="longestStreak", ge=0)
    last_active_date: str = Field(alias="lastActiveDate", min_length=10, max_length=10)

    @validator("last_active_date")
    def validate_iso_date(cls, value: str) -> str:
        try:
            datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("lastActiveDate must be an ISO date, for example 2026-06-24") from exc
        return value


class SchoolPayload(ApiModel):
    id: Annotated[str, Field(min_length=1, max_length=128)]
    name: Annotated[str, Field(min_length=1, max_length=256)]
    district: str = Field(max_length=256)
    state: str = Field(max_length=128)


class TeacherPayload(ApiModel):
    id: Annotated[str, Field(min_length=1, max_length=128)]
    school_id: Annotated[str, Field(alias="schoolId", min_length=1, max_length=128)]
    name: Annotated[str, Field(min_length=1, max_length=256)]
    email: Annotated[str, Field(min_length=3, max_length=320)]
    role: Literal["TEACHER", "ADMIN"]

    @validator("email")
    def validate_email(cls, value: str) -> str:
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("email must be a valid email address")
        return value.lower()


class ClassPayload(ApiModel):
    id: Annotated[str, Field(min_length=1, max_length=128)]
    school_id: Annotated[str, Field(alias="schoolId", min_length=1, max_length=128)]
    teacher_id: Annotated[str, Field(alias="teacherId", min_length=1, max_length=128)]
    name: Annotated[str, Field(min_length=1, max_length=256)]


class StudentPayload(ApiModel):
    id: Annotated[str, Field(min_length=1, max_length=128)]
    school_id: Annotated[str, Field(alias="schoolId", min_length=1, max_length=128)]
    class_id: str | None = Field(alias="classId", default=None, max_length=128)
    name: Annotated[str, Field(min_length=1, max_length=256)]
    grade: str = Field(max_length=64)
    accessibility_needs: str = Field(alias="accessibilityNeeds", default="", max_length=1000)


LEVELS = (
    (1, "Dot Explorer", "Learn the six Braille dot positions.", ["Explore all six dots"]),
    (2, "Letter Builder", "Build English letters from dots.", [f"Letter {letter}" for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"]),
    (3, "Letter Recognition", "Identify Braille letters from their dot patterns.", ["Letter recognition practice"]),
    (4, "Word Reading", "Read simple Braille words cell by cell.", ["Read cat", "Read dog", "Read big", "Read sun", "Read cup", "Read bus", "Read pen", "Read fan", "Read mat", "Read run"]),
    (5, "Grade 2 Contractions", "Learn common contractions used in Braille books.", ["the", "and", "for", "of", "with", "child", "shall", "this", "which", "out", "still"]),
    (6, "Scan and Learn", "Practice with real Braille scans.", ["Scan your own Braille page"]),
)


def curriculum_payload(level: int | None = None) -> dict[str, Any]:
    selected = [item for item in LEVELS if level is None or item[0] == level]
    return {
        "version": 1,
        "levels": [
            {
                "level": number,
                "title": title,
                "lessons": [
                    LessonPayload(
                        id=f"level-{number}-{index + 1}",
                        title=lesson_title,
                        description=description,
                        orderIndex=index,
                        isPremium=False,
                    ).dict(by_alias=True)
                    for index, lesson_title in enumerate(lesson_titles)
                ],
            }
            for number, title, description, lesson_titles in selected
        ],
    }


class LmsStore:
    """Small SQLite store; each operation opens its own connection for safe API concurrency."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self._lock = threading.Lock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS lms_progress (
                    user_id TEXT NOT NULL,
                    lesson_id TEXT NOT NULL,
                    level INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    accuracy REAL NOT NULL,
                    completed_at INTEGER,
                    updated_at INTEGER NOT NULL,
                    PRIMARY KEY (user_id, lesson_id)
                );
                CREATE TABLE IF NOT EXISTS lms_scores (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    lesson_id TEXT NOT NULL,
                    question_id TEXT NOT NULL,
                    user_answer TEXT NOT NULL,
                    correct_answer TEXT NOT NULL,
                    is_correct INTEGER NOT NULL,
                    timestamp INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS lms_activity (
                    user_id TEXT NOT NULL,
                    activity_date TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    PRIMARY KEY (user_id, activity_date)
                );
                CREATE TABLE IF NOT EXISTS lms_streaks (
                    user_id TEXT PRIMARY KEY,
                    current_streak INTEGER NOT NULL,
                    longest_streak INTEGER NOT NULL,
                    last_active_date TEXT NOT NULL,
                    updated_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS schools (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    district TEXT NOT NULL,
                    state TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS teachers (
                    id TEXT PRIMARY KEY,
                    school_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    role TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS classes (
                    id TEXT PRIMARY KEY,
                    school_id TEXT NOT NULL,
                    teacher_id TEXT NOT NULL,
                    name TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS students (
                    id TEXT PRIMARY KEY,
                    school_id TEXT NOT NULL,
                    class_id TEXT,
                    name TEXT NOT NULL,
                    grade TEXT NOT NULL,
                    accessibility_needs TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS student_lesson_progress (
                    student_id TEXT NOT NULL,
                    lesson_id TEXT NOT NULL,
                    level INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    accuracy REAL NOT NULL,
                    completed_at INTEGER,
                    PRIMARY KEY (student_id, lesson_id)
                );
                CREATE INDEX IF NOT EXISTS idx_lms_progress_user ON lms_progress(user_id);
                CREATE INDEX IF NOT EXISTS idx_lms_scores_user ON lms_scores(user_id);
                CREATE INDEX IF NOT EXISTS idx_students_class ON students(class_id);
                CREATE INDEX IF NOT EXISTS idx_student_lesson_progress_student ON student_lesson_progress(student_id);
                """
            )
            connection.execute(
                """
                INSERT OR REPLACE INTO student_lesson_progress
                (student_id, lesson_id, level, status, score, accuracy, completed_at)
                SELECT user_id, lesson_id, level, status, score, accuracy, completed_at FROM lms_progress
                """
            )

    def upsert_progress(self, payload: ProgressPayload) -> dict[str, Any]:
        now = _now_millis()
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO lms_progress (user_id, lesson_id, level, status, score, accuracy, completed_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, lesson_id) DO UPDATE SET
                    level=excluded.level, status=excluded.status, score=excluded.score,
                    accuracy=excluded.accuracy, completed_at=excluded.completed_at, updated_at=excluded.updated_at
                """,
                (payload.user_id, payload.lesson_id, payload.level, payload.status, payload.score,
                 payload.accuracy, payload.completed_at, now),
            )
            connection.execute(
                """
                INSERT INTO student_lesson_progress
                (student_id, lesson_id, level, status, score, accuracy, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(student_id, lesson_id) DO UPDATE SET
                    level=excluded.level, status=excluded.status, score=excluded.score,
                    accuracy=excluded.accuracy, completed_at=excluded.completed_at
                """,
                (payload.user_id, payload.lesson_id, payload.level, payload.status, payload.score,
                 payload.accuracy, payload.completed_at),
            )
            self._record_activity(connection, payload.user_id, payload.completed_at or now)
        return {"ok": True, "syncStatus": "SYNCED", "updatedAt": now}

    def insert_score(self, payload: ScorePayload) -> dict[str, Any]:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO lms_scores (id, user_id, lesson_id, question_id, user_answer, correct_answer, is_correct, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    user_answer=excluded.user_answer, correct_answer=excluded.correct_answer,
                    is_correct=excluded.is_correct, timestamp=excluded.timestamp
                """,
                (payload.id, payload.user_id, payload.lesson_id, payload.question_id,
                 payload.user_answer, payload.correct_answer, int(payload.is_correct), payload.timestamp),
            )
            self._record_activity(connection, payload.user_id, payload.timestamp)
        return {"ok": True, "syncStatus": "SYNCED", "id": payload.id}

    def upsert_streak(self, payload: StreakPayload) -> dict[str, Any]:
        now = _now_millis()
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO lms_streaks (user_id, current_streak, longest_streak, last_active_date, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    current_streak=excluded.current_streak, longest_streak=excluded.longest_streak,
                    last_active_date=excluded.last_active_date, updated_at=excluded.updated_at
                """,
                (payload.user_id, payload.current_streak, payload.longest_streak, payload.last_active_date, now),
            )
        return {"ok": True, "syncStatus": "SYNCED", "updatedAt": now}

    def get_progress(self, user_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM lms_progress WHERE user_id = ? ORDER BY level, lesson_id", (user_id,)
            ).fetchall()
        return [_camel_progress(row) for row in rows]

    def student_analytics(self, user_id: str) -> dict[str, Any]:
        progress = self.get_progress(user_id)
        completed = [item for item in progress if item["status"] == "COMPLETED"]
        levels = _level_progress(progress)
        with self._connect() as connection:
            score_rows = connection.execute(
                "SELECT correct_answer, is_correct FROM lms_scores WHERE user_id = ?", (user_id,)
            ).fetchall()
            scan_practice_count = connection.execute(
                "SELECT COUNT(*) FROM lms_progress WHERE user_id = ? AND level = 6 AND status = 'COMPLETED'",
                (user_id,),
            ).fetchone()[0]
            active_days = [
                row[0] for row in connection.execute(
                    "SELECT activity_date FROM lms_activity WHERE user_id = ? ORDER BY activity_date", (user_id,)
                ).fetchall()
            ]
            stored_streak = connection.execute(
                "SELECT current_streak, longest_streak FROM lms_streaks WHERE user_id = ?", (user_id,)
            ).fetchone()
        return {
            "userId": user_id,
            "totalLessonsCompleted": len(completed),
            "levelProgress": levels,
            "accuracyByLetter": _accuracy_by_letter(score_rows),
            "streak": {
                "currentStreak": stored_streak["current_streak"],
                "longestStreak": stored_streak["longest_streak"],
            } if stored_streak else _streak(active_days),
            "scanPracticeCount": scan_practice_count,
        }

    def class_analytics(self, class_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            class_row = connection.execute(
                "SELECT id, school_id, teacher_id, name FROM classes WHERE id = ?", (class_id,)
            ).fetchone()
            if class_row is None:
                raise LookupError("Class not found")
            students = connection.execute(
                "SELECT id, name, grade, accessibility_needs FROM students WHERE class_id = ? ORDER BY name", (class_id,)
            ).fetchall()
            score_rows = connection.execute(
                """
                SELECT s.correct_answer, s.is_correct FROM lms_scores s
                JOIN students st ON st.id = s.user_id WHERE st.class_id = ?
                """, (class_id,)
            ).fetchall()
            details = [self._student_dashboard_row(connection, student) for student in students]
        total_lessons = _curriculum_lesson_count()
        completion = [student["completionPercentage"] for student in details]
        grade_two = [student["grade2ContractionProgress"] for student in details]
        return {
            "classId": class_row["id"],
            "className": class_row["name"],
            "schoolId": class_row["school_id"],
            "teacherId": class_row["teacher_id"],
            "studentCount": len(details),
            "classCompletionPercentage": round(sum(completion) / len(completion), 2) if completion else 0.0,
            "totalCurriculumLessons": total_lessons,
            "studentsFallingBehind": [student for student in details if student["isFallingBehind"]],
            "accuracyByLetter": _accuracy_by_letter(score_rows),
            "scanPracticeCount": sum(student["scanPracticeCount"] for student in details),
            "grade2ContractionProgress": {
                "completedLessons": sum(item["completedLessons"] for item in grade_two),
                "totalLessonsPerStudent": _lesson_count_for_level(5),
                "averagePercentage": round(
                    sum(item["percentage"] for item in grade_two) / len(grade_two), 2
                ) if grade_two else 0.0,
            },
            "students": details,
        }

    def create_school(self, payload: SchoolPayload) -> dict[str, Any]:
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT INTO schools (id, name, district, state, created_at) VALUES (?, ?, ?, ?, ?)",
                (payload.id, payload.name, payload.district, payload.state, _now_millis()),
            )
        return {"ok": True, "id": payload.id}

    def create_teacher(self, payload: TeacherPayload) -> dict[str, Any]:
        with self._lock, self._connect() as connection:
            self._require_school(connection, payload.school_id)
            connection.execute(
                "INSERT INTO teachers (id, school_id, name, email, role) VALUES (?, ?, ?, ?, ?)",
                (payload.id, payload.school_id, payload.name, payload.email, payload.role),
            )
        return {"ok": True, "id": payload.id}

    def create_class(self, payload: ClassPayload) -> dict[str, Any]:
        with self._lock, self._connect() as connection:
            self._require_school(connection, payload.school_id)
            teacher = connection.execute("SELECT school_id FROM teachers WHERE id = ?", (payload.teacher_id,)).fetchone()
            if teacher is None or teacher["school_id"] != payload.school_id:
                raise ValueError("teacherId must belong to the specified school")
            connection.execute(
                "INSERT INTO classes (id, school_id, teacher_id, name) VALUES (?, ?, ?, ?)",
                (payload.id, payload.school_id, payload.teacher_id, payload.name),
            )
        return {"ok": True, "id": payload.id}

    def create_student(self, payload: StudentPayload) -> dict[str, Any]:
        with self._lock, self._connect() as connection:
            self._require_school(connection, payload.school_id)
            if payload.class_id is not None:
                class_row = connection.execute("SELECT school_id FROM classes WHERE id = ?", (payload.class_id,)).fetchone()
                if class_row is None or class_row["school_id"] != payload.school_id:
                    raise ValueError("classId must belong to the specified school")
            connection.execute(
                """
                INSERT INTO students (id, school_id, class_id, name, grade, accessibility_needs)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    school_id=excluded.school_id, class_id=excluded.class_id, name=excluded.name,
                    grade=excluded.grade, accessibility_needs=excluded.accessibility_needs
                """,
                (payload.id, payload.school_id, payload.class_id, payload.name, payload.grade, payload.accessibility_needs),
            )
        return {"ok": True, "id": payload.id}

    def class_export_csv(self, class_id: str) -> str:
        dashboard = self.class_analytics(class_id)
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "studentId", "name", "grade", "completedLessons", "totalLessons",
            "completionPercentage", "scanPracticeCount", "grade2CompletedLessons",
            "grade2TotalLessons", "grade2Percentage", "averageLetterAccuracy", "lastActivityAt",
        ])
        writer.writeheader()
        for student in dashboard["students"]:
            grade_two = student["grade2ContractionProgress"]
            writer.writerow({
                "studentId": student["studentId"], "name": student["name"], "grade": student["grade"],
                "completedLessons": student["completedLessons"], "totalLessons": student["totalLessons"],
                "completionPercentage": student["completionPercentage"], "scanPracticeCount": student["scanPracticeCount"],
                "grade2CompletedLessons": grade_two["completedLessons"],
                "grade2TotalLessons": grade_two["totalLessons"], "grade2Percentage": grade_two["percentage"],
                "averageLetterAccuracy": student["averageLetterAccuracy"], "lastActivityAt": student["lastActivityAt"],
            })
        return output.getvalue()

    def student_report(self, student_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            student = connection.execute(
                "SELECT id, school_id, class_id, name, grade, accessibility_needs FROM students WHERE id = ?",
                (student_id,),
            ).fetchone()
            if student is None:
                raise LookupError("Student not found")
            progress = connection.execute(
                "SELECT * FROM student_lesson_progress WHERE student_id = ?", (student_id,)
            ).fetchall()
            score_rows = connection.execute(
                "SELECT correct_answer, is_correct FROM lms_scores WHERE user_id = ?", (student_id,)
            ).fetchall()
            streak_row = connection.execute(
                "SELECT current_streak, longest_streak FROM lms_streaks WHERE user_id = ?", (student_id,)
            ).fetchone()
            active_days = [row[0] for row in connection.execute(
                "SELECT activity_date FROM lms_activity WHERE user_id = ? ORDER BY activity_date", (student_id,)
            ).fetchall()]

        completed = [row for row in progress if row["status"] == "COMPLETED"]
        current_level = _current_level(progress)
        words_practiced = sum(
            row["level"] == 4 and row["status"] != "NOT_STARTED" for row in progress
        )
        scan_practice_count = sum(
            row["level"] == 6 and row["status"] == "COMPLETED" for row in progress
        )
        return {
            "studentId": student["id"], "studentName": student["name"], "schoolId": student["school_id"],
            "classId": student["class_id"], "grade": student["grade"],
            "accessibilityNeeds": student["accessibility_needs"], "lessonsCompleted": len(completed),
            "totalLessons": _curriculum_lesson_count(), "currentLevel": current_level,
            "accuracyByLetter": _accuracy_by_letter(score_rows), "wordsPracticed": words_practiced,
            "scanPracticeCount": scan_practice_count,
            "streak": {
                "currentStreak": streak_row["current_streak"],
                "longestStreak": streak_row["longest_streak"],
            } if streak_row else _streak(active_days),
        }

    def class_report(self, class_id: str) -> dict[str, Any]:
        dashboard = self.class_analytics(class_id)
        with self._connect() as connection:
            score_rows = connection.execute(
                """
                SELECT s.correct_answer, s.is_correct FROM lms_scores s
                JOIN students st ON st.id = s.user_id WHERE st.class_id = ?
                """, (class_id,)
            ).fetchall()
        missed = _most_missed_letters(score_rows)
        return {
            "classId": dashboard["classId"], "className": dashboard["className"],
            "numberOfStudents": dashboard["studentCount"],
            "averageCompletion": dashboard["classCompletionPercentage"],
            "averageAccuracy": _average_accuracy(score_rows),
            "studentsNeedingHelp": dashboard["studentsFallingBehind"],
            "mostMissedLetters": missed,
            "students": dashboard["students"],
        }

    def curriculum_completion_report(self, class_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            class_row = connection.execute("SELECT id, name FROM classes WHERE id = ?", (class_id,)).fetchone()
            if class_row is None:
                raise LookupError("Class not found")
            student_count = connection.execute(
                "SELECT COUNT(*) FROM students WHERE class_id = ?", (class_id,)
            ).fetchone()[0]
            rows = connection.execute(
                """
                SELECT p.level, p.status FROM student_lesson_progress p
                JOIN students s ON s.id = p.student_id WHERE s.class_id = ?
                """, (class_id,)
            ).fetchall()
        levels = []
        for number, title, _description, lessons in LEVELS:
            completed = sum(row["level"] == number and row["status"] == "COMPLETED" for row in rows)
            possible = student_count * len(lessons)
            levels.append({
                "level": number, "title": title, "completedLessons": completed,
                "possibleLessons": possible,
                "completionPercentage": round((completed / possible) * 100, 2) if possible else 0.0,
            })
        grade_one_levels = [item for item in levels if item["level"] <= 4]
        grade_one_completed = sum(item["completedLessons"] for item in grade_one_levels)
        grade_one_possible = sum(item["possibleLessons"] for item in grade_one_levels)
        grade_two = next(item for item in levels if item["level"] == 5)
        scan_practice = next(item for item in levels if item["level"] == 6)
        return {
            "classId": class_row["id"], "className": class_row["name"], "studentCount": student_count,
            "levelWiseCompletion": levels,
            "grade1Completion": {
                "completedLessons": grade_one_completed, "possibleLessons": grade_one_possible,
                "completionPercentage": round((grade_one_completed / grade_one_possible) * 100, 2)
                if grade_one_possible else 0.0,
            },
            "grade2ContractionProgress": grade_two,
            "realWorldScanPracticeCompletion": scan_practice,
        }

    def student_report_csv(self, student_id: str) -> str:
        report = self.student_report(student_id)
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "studentId", "studentName", "grade", "currentLevel", "lessonsCompleted", "totalLessons",
            "wordsPracticed", "scanPracticeCount", "currentStreak", "longestStreak", "letter", "letterAccuracy",
        ])
        writer.writeheader()
        letter_accuracy = report["accuracyByLetter"] or {"": ""}
        for letter, accuracy in letter_accuracy.items():
            writer.writerow({
                "studentId": report["studentId"], "studentName": report["studentName"], "grade": report["grade"],
                "currentLevel": report["currentLevel"], "lessonsCompleted": report["lessonsCompleted"],
                "totalLessons": report["totalLessons"], "wordsPracticed": report["wordsPracticed"],
                "scanPracticeCount": report["scanPracticeCount"],
                "currentStreak": report["streak"]["currentStreak"],
                "longestStreak": report["streak"]["longestStreak"], "letter": letter, "letterAccuracy": accuracy,
            })
        return output.getvalue()

    def curriculum_completion_csv(self, class_id: str) -> str:
        report = self.curriculum_completion_report(class_id)
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "classId", "className", "studentCount", "level", "title", "completedLessons",
            "possibleLessons", "completionPercentage",
        ])
        writer.writeheader()
        for level in report["levelWiseCompletion"]:
            writer.writerow({
                "classId": report["classId"], "className": report["className"],
                "studentCount": report["studentCount"], **level,
            })
        return output.getvalue()

    @staticmethod
    def _require_school(connection: sqlite3.Connection, school_id: str) -> None:
        if connection.execute("SELECT 1 FROM schools WHERE id = ?", (school_id,)).fetchone() is None:
            raise LookupError("School not found")

    @staticmethod
    def _student_dashboard_row(connection: sqlite3.Connection, student: sqlite3.Row) -> dict[str, Any]:
        progress = connection.execute(
            "SELECT * FROM student_lesson_progress WHERE student_id = ?", (student["id"],)
        ).fetchall()
        completed = [row for row in progress if row["status"] == "COMPLETED"]
        total = _curriculum_lesson_count()
        completion_percentage = round((len(completed) / total) * 100, 2) if total else 0.0
        grade_two_total = _lesson_count_for_level(5)
        grade_two_completed = sum(row["status"] == "COMPLETED" and row["level"] == 5 for row in progress)
        score_rows = connection.execute(
            "SELECT correct_answer, is_correct FROM lms_scores WHERE user_id = ?", (student["id"],)
        ).fetchall()
        average_accuracy = _average_accuracy(score_rows)
        last_activity = connection.execute(
            "SELECT MAX(timestamp) FROM lms_activity WHERE user_id = ?", (student["id"],)
        ).fetchone()[0]
        inactive = last_activity is None or (_now_millis() - last_activity) > 7 * 24 * 60 * 60 * 1000
        return {
            "studentId": student["id"], "name": student["name"], "grade": student["grade"],
            "accessibilityNeeds": student["accessibility_needs"], "completedLessons": len(completed),
            "totalLessons": total, "completionPercentage": completion_percentage,
            "isFallingBehind": completion_percentage < 50.0 or inactive,
            "fallingBehindReason": "No activity in the last 7 days" if inactive else (
                "Below 50% curriculum completion" if completion_percentage < 50.0 else ""
            ),
            "scanPracticeCount": sum(row["status"] == "COMPLETED" and row["level"] == 6 for row in progress),
            "grade2ContractionProgress": {
                "completedLessons": grade_two_completed,
                "totalLessons": grade_two_total,
                "percentage": round((grade_two_completed / grade_two_total) * 100, 2) if grade_two_total else 0.0,
            },
            "averageLetterAccuracy": average_accuracy, "lastActivityAt": last_activity,
        }

    @staticmethod
    def _record_activity(connection: sqlite3.Connection, user_id: str, timestamp: int) -> None:
        date = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc).date().isoformat()
        connection.execute(
            "INSERT OR REPLACE INTO lms_activity (user_id, activity_date, timestamp) VALUES (?, ?, ?)",
            (user_id, date, timestamp),
        )


def _now_millis() -> int:
    return int(datetime.now(tz=timezone.utc).timestamp() * 1000)


def _camel_progress(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "userId": row["user_id"], "lessonId": row["lesson_id"], "level": row["level"],
        "status": row["status"], "score": row["score"], "accuracy": row["accuracy"],
        "completedAt": row["completed_at"], "updatedAt": row["updated_at"],
    }


def _level_progress(progress: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for level, title, _description, lessons in LEVELS:
        level_progress = [item for item in progress if item["level"] == level]
        completed = sum(item["status"] == "COMPLETED" for item in level_progress)
        result.append({
            "level": level,
            "title": title,
            "completedLessons": completed,
            "totalLessons": len(lessons),
            "progress": round(completed / len(lessons), 4) if lessons else 0.0,
        })
    return result


def _lesson_count_for_level(level: int) -> int:
    return next((len(lessons) for number, _title, _description, lessons in LEVELS if number == level), 0)


def _curriculum_lesson_count() -> int:
    return sum(len(lessons) for _number, _title, _description, lessons in LEVELS)


def _current_level(progress: list[sqlite3.Row]) -> int:
    for level, _title, _description, lessons in LEVELS:
        completed = sum(row["level"] == level and row["status"] == "COMPLETED" for row in progress)
        if completed < len(lessons):
            return level
    return 6


def _accuracy_by_letter(rows: list[sqlite3.Row]) -> dict[str, float]:
    grouped: dict[str, list[int]] = {}
    for row in rows:
        letter = row["correct_answer"].upper()
        if len(letter) == 1 and letter.isalpha():
            grouped.setdefault(letter, []).append(row["is_correct"])
    return {letter: round(sum(scores) / len(scores), 4) for letter, scores in sorted(grouped.items())}


def _average_accuracy(rows: list[sqlite3.Row]) -> float | None:
    if not rows:
        return None
    return round(sum(row["is_correct"] for row in rows) / len(rows), 4)


def _most_missed_letters(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    missed: dict[str, int] = {}
    for row in rows:
        letter = row["correct_answer"].upper()
        if not row["is_correct"] and len(letter) == 1 and letter.isalpha():
            missed[letter] = missed.get(letter, 0) + 1
    return [
        {"letter": letter, "missedCount": count}
        for letter, count in sorted(missed.items(), key=lambda item: (-item[1], item[0]))[:5]
    ]


def _streak(active_days: list[str]) -> dict[str, int]:
    if not active_days:
        return {"currentStreak": 0, "longestStreak": 0}
    dates = [datetime.fromisoformat(day).date() for day in active_days]
    longest = current = 1
    for previous, date in zip(dates, dates[1:]):
        if (date - previous).days == 1:
            current += 1
        else:
            current = 1
        longest = max(longest, current)
    today = datetime.now(tz=timezone.utc).date()
    recent = dates[-1]
    current_streak = current if (today - recent).days <= 1 else 0
    return {"currentStreak": current_streak, "longestStreak": longest}


async def require_lms_auth(
    authorization: str | None = Header(default=None),
) -> None:
    """TODO: validate a real bearer token or gateway identity before production deployment."""
    del authorization
    # Deliberately no fake token scheme or user identity is accepted here.
    return None


STORE = LmsStore(Path(os.environ.get("LMS_DATABASE_PATH", Path(__file__).with_name("lms_progress.db"))))
LmsAuth = Depends(require_lms_auth)


@router.get("/curriculum")
async def get_curriculum(_: None = LmsAuth) -> dict[str, Any]:
    return curriculum_payload()


@router.get("/curriculum/{level}")
async def get_curriculum_level(level: int, _: None = LmsAuth) -> dict[str, Any]:
    if level < 1 or level > 6:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curriculum level must be between 1 and 6")
    return curriculum_payload(level)


@router.post("/progress")
async def post_progress(payload: ProgressPayload, _: None = LmsAuth) -> dict[str, Any]:
    return STORE.upsert_progress(payload)


@router.get("/progress/{user_id}")
async def get_progress(user_id: str, _: None = LmsAuth) -> dict[str, Any]:
    if not user_id.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="userId is required")
    return {"userId": user_id, "progress": STORE.get_progress(user_id)}


@router.post("/scores")
async def post_score(payload: ScorePayload, _: None = LmsAuth) -> dict[str, Any]:
    return STORE.insert_score(payload)


@router.post("/streaks")
async def post_streak(payload: StreakPayload, _: None = LmsAuth) -> dict[str, Any]:
    return STORE.upsert_streak(payload)


@router.post("/admin/schools", status_code=status.HTTP_201_CREATED)
async def post_school(payload: SchoolPayload, _: None = LmsAuth) -> dict[str, Any]:
    return _admin_write(lambda: STORE.create_school(payload))


@router.post("/admin/teachers", status_code=status.HTTP_201_CREATED)
async def post_teacher(payload: TeacherPayload, _: None = LmsAuth) -> dict[str, Any]:
    return _admin_write(lambda: STORE.create_teacher(payload))


@router.post("/admin/classes", status_code=status.HTTP_201_CREATED)
async def post_class(payload: ClassPayload, _: None = LmsAuth) -> dict[str, Any]:
    return _admin_write(lambda: STORE.create_class(payload))


@router.post("/admin/students", status_code=status.HTTP_201_CREATED)
async def post_student(payload: StudentPayload, _: None = LmsAuth) -> dict[str, Any]:
    return _admin_write(lambda: STORE.create_student(payload))


@router.get("/analytics/student/{user_id}")
async def get_student_analytics(user_id: str, _: None = LmsAuth) -> dict[str, Any]:
    if not user_id.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="userId is required")
    return STORE.student_analytics(user_id)


@router.get("/analytics/class/{class_id}")
async def get_class_analytics(class_id: str, _: None = LmsAuth) -> dict[str, Any]:
    if not class_id.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="classId is required")
    try:
        return STORE.class_analytics(class_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/admin/classes/{class_id}/dashboard")
async def get_admin_class_dashboard(class_id: str, _: None = LmsAuth) -> dict[str, Any]:
    try:
        return STORE.class_analytics(class_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/admin/classes/{class_id}/export.csv")
async def get_class_export(class_id: str, _: None = LmsAuth) -> StreamingResponse:
    try:
        export = STORE.class_export_csv(class_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return StreamingResponse(
        iter([export]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="sciobraille-class-{class_id}.csv"'},
    )


@router.get("/reports/students/{student_id}")
async def get_student_report(student_id: str, _: None = LmsAuth) -> dict[str, Any]:
    try:
        return STORE.student_report(student_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/reports/students/{student_id}/export.csv")
async def get_student_report_export(student_id: str, _: None = LmsAuth) -> StreamingResponse:
    try:
        export = STORE.student_report_csv(student_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return StreamingResponse(
        iter([export]), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="sciobraille-student-{student_id}.csv"'},
    )


@router.get("/reports/classes/{class_id}")
async def get_class_report(class_id: str, _: None = LmsAuth) -> dict[str, Any]:
    try:
        return STORE.class_report(class_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/reports/classes/{class_id}/export.csv")
async def get_class_report_export(class_id: str, _: None = LmsAuth) -> StreamingResponse:
    try:
        export = STORE.class_export_csv(class_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return StreamingResponse(
        iter([export]), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="sciobraille-class-report-{class_id}.csv"'},
    )


@router.get("/reports/classes/{class_id}/curriculum")
async def get_curriculum_completion_report(class_id: str, _: None = LmsAuth) -> dict[str, Any]:
    try:
        return STORE.curriculum_completion_report(class_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/reports/classes/{class_id}/curriculum/export.csv")
async def get_curriculum_completion_export(class_id: str, _: None = LmsAuth) -> StreamingResponse:
    try:
        export = STORE.curriculum_completion_csv(class_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return StreamingResponse(
        iter([export]), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="sciobraille-curriculum-{class_id}.csv"'},
    )


def _admin_write(operation: Any) -> dict[str, Any]:
    try:
        return operation()
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A record with this id or email already exists") from exc
