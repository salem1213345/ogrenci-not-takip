CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_no TEXT NOT NULL UNIQUE,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT
);

CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    credit INTEGER NOT NULL CHECK (credit > 0),
    midterm_weight REAL NOT NULL DEFAULT 40,
    final_weight REAL NOT NULL DEFAULT 60
);

CREATE TABLE IF NOT EXISTS enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    term TEXT NOT NULL,
    UNIQUE (student_id, course_id, term)
);

CREATE TABLE IF NOT EXISTS grades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    enrollment_id INTEGER NOT NULL UNIQUE
        REFERENCES enrollments(id) ON DELETE CASCADE,
    midterm REAL CHECK (midterm BETWEEN 0 AND 100),
    final REAL CHECK (final BETWEEN 0 AND 100),
    assignment REAL CHECK (assignment BETWEEN 0 AND 100),
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'teacher'))
);

CREATE INDEX IF NOT EXISTS idx_students_no ON students(student_no);
CREATE INDEX IF NOT EXISTS idx_enroll_course ON enrollments(course_id);
