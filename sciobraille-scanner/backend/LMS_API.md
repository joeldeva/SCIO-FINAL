# Sciobraille LMS Sync API

Base path: `/api`. The scanner APIs (`/api/health`, `/api/scan-frame`, and `/ws/scan`) are unchanged.

## Authentication

**Security warning:** Run these LMS endpoints only on a trusted local network during prototype testing. This backend has no authentication provider. The `require_lms_auth` dependency is a deliberate TODO boundary and currently accepts every request. Do not expose this service publicly. Before deployment, protect every LMS endpoint with a real bearer-token validator or authenticated API gateway, enforce that the authenticated user matches `userId`, and restrict class analytics to authorized teachers.

All request and response timestamps are Unix milliseconds. Progress `accuracy` is normalized from `0.0` to `1.0`; the Android client should divide its local percentage by 100 before upload.

## Curriculum

### `GET /api/curriculum`

Returns versioned levels and lessons for the complete curriculum.

```json
{
  "version": 1,
  "levels": [{ "level": 1, "title": "Dot Explorer", "lessons": [] }]
}
```

### `GET /api/curriculum/{level}`

Returns the same shape, restricted to a level from 1 through 6. Invalid levels return `404`.

## Progress

### `POST /api/progress`

Upserts one lesson progress record by `(userId, lessonId)`.

```json
{
  "userId": "user-123",
  "lessonId": "level-1-1",
  "level": 1,
  "status": "COMPLETED",
  "score": 100,
  "accuracy": 1.0,
  "completedAt": 1735689600000
}
```

`status` is one of `NOT_STARTED`, `IN_PROGRESS`, or `COMPLETED`. Successful responses include `syncStatus: "SYNCED"` and `updatedAt`.

### `GET /api/progress/{userId}`

Returns all synced progress records for the user.

## Question Scores

### `POST /api/scores`

Upserts one idempotent, question-level answer using the client-generated `id`.

```json
{
  "id": "score-uuid",
  "userId": "user-123",
  "lessonId": "level-3-recognition",
  "questionId": "question-7",
  "userAnswer": "K",
  "correctAnswer": "K",
  "isCorrect": true,
  "timestamp": 1735689600000
}
```

## Streaks

### `POST /api/streaks`

Upserts the locally calculated streak. The Android device remains the source of truth for
offline activity; this endpoint mirrors the latest value for cross-device analytics.

```json
{
  "userId": "user-123",
  "currentStreak": 4,
  "longestStreak": 12,
  "lastActiveDate": "2026-06-24"
}
```

## Analytics

### `GET /api/analytics/student/{userId}`

Returns total completed lessons, each level's completion ratio, recognition accuracy by letter, current and longest streak, and completed Level 6 scan practice count.

### `GET /api/analytics/class/{classId}`

Returns the teacher dashboard for a registered class: class completion percentage, students falling behind, accuracy by letter, scan practice count, Grade 2 contraction progress, and student-level summaries.

## School Dashboard Administration

These endpoints create the roster used by class analytics. In production they must be restricted to authorized school administrators and teachers.

### `POST /api/admin/schools`

```json
{ "id": "school-1", "name": "Central School", "district": "Central", "state": "Kerala" }
```

### `POST /api/admin/teachers`

```json
{
  "id": "teacher-1", "schoolId": "school-1", "name": "Asha Nair",
  "email": "asha@example.org", "role": "TEACHER"
}
```

### `POST /api/admin/classes`

```json
{ "id": "class-7a", "schoolId": "school-1", "teacherId": "teacher-1", "name": "Grade 7 A" }
```

### `POST /api/admin/students`

The student `id` must equal the Android LMS `userId` for already-synced progress to appear automatically in the dashboard.

```json
{
  "id": "device-android-installation-id", "schoolId": "school-1", "classId": "class-7a",
  "name": "Student Name", "grade": "7", "accessibilityNeeds": "Screen reader and audio-first lessons"
}
```

### `GET /api/admin/classes/{classId}/dashboard`

Returns the same detailed class dashboard as `GET /api/analytics/class/{classId}`.

### `GET /api/admin/classes/{classId}/export.csv`

Downloads a CSV with one row per student, including completion, scan practice, Grade 2 progress, letter accuracy, and last activity.

## School-ready Reports

PDF generation is not included because this backend has no existing PDF library. The CSV exports are designed for school spreadsheets and reporting workflows.

### Student Progress Report

- `GET /api/reports/students/{studentId}` returns the student name, lessons completed, current level, accuracy by letter, words practiced, scan practice count, and streak.
- `GET /api/reports/students/{studentId}/export.csv` downloads the same report in CSV form. It has one row per practiced letter so accuracy stays spreadsheet-friendly.

### Class Progress Report

- `GET /api/reports/classes/{classId}` returns class name, student count, average completion, average accuracy, students needing help, and the five most missed letters.
- `GET /api/reports/classes/{classId}/export.csv` downloads per-student class report rows.

### Curriculum Completion Report

- `GET /api/reports/classes/{classId}/curriculum` returns level-wise completion plus aggregated Grade 1, Grade 2 contraction, and real-world scan practice completion.
- `GET /api/reports/classes/{classId}/curriculum/export.csv` downloads the level-wise report as CSV.

## Offline Sync Behavior

Android remains the source of truth while offline. It persists `NOT_SYNCED` Room records first, then later sends idempotent progress and score IDs when a real authenticated backend is configured. The current `SyncManager` intentionally makes no network calls until that configuration exists.
