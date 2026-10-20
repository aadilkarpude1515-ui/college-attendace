# CampusFlow — College Attendance Management (Flask + SQLite)

A staged starter implementation with student, teacher and admin dashboards, attendance, leave requests, syllabus resources, quizzes and account security.

## Features included
- Role-based login for students, teachers and admins.
- Password hashing, account activation, mandatory first-login password change, login ID/password updates.
- Student dashboard with overall and subject-wise attendance, leave request status and quizzes.
- Teacher attendance marking for assigned subject/batch combinations.
- Attendance correction through re-saving the same subject/batch/date session; unique constraints prevent duplicate sessions/records.
- Leave approval restricted to the assigned class teacher.
- Teacher quiz creation and automatic grading for one MCQ per quiz.
- Admin creation of students, teachers, batches, semesters, subjects, subject/batch assignments and class-teacher assignments.
- Syllabus text and optional file upload.
- Account deactivation, teacher password reset and recent audit log.
- Claymorphism-inspired responsive interface.

## Requirements
Python 3.10+ recommended.

## macOS setup
```bash
cd college_attendance
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Change `SECRET_KEY` in `.env` to a long random value. For local development only, the default admin login is `admin` / `admin123`. The app forces a password change on first login. You can set `INITIAL_ADMIN_ID` and `INITIAL_ADMIN_PASSWORD` before the first launch.

Start the app:
```bash
python3 app.py
```
Open http://127.0.0.1:5000.

The database is created at `instance/college.db`. The app seeds one batch and semesters 1–8 on first startup.

## First-run workflow
1. Sign in with the initial admin credentials and change the password.
2. In Admin, create a batch if needed (a starter batch `CSE-A` is included).
3. Add semesters if the desired semester is not listed.
4. Add subjects.
5. Add teachers and students. Student initial password is the PRN. Teacher initial password is either the one entered or auto-generated and shown once after creation.
6. Assign teachers to each subject/batch combination.
7. Assign class teachers to batches.
8. Add syllabus entries.
9. Teachers sign in, change temporary password, mark attendance and create quizzes.
10. Students sign in, change their initial password, review attendance, apply for leave and take quizzes.

## Important limitations in this starter
- The admin panel currently supports create operations for core academic entities; editing/deleting batches, subjects and assignments should be added before production.
- Student "delete" is implemented as account deactivation so historic attendance/audit records remain available.
- Quiz creation currently supports one multiple-choice question per quiz. A later stage can add multi-question editing, quiz timers and richer results.
- Syllabus listing currently shows entries from all semesters. Add enrollment/semester-specific filtering for a production rollout.
- Approved leave does not automatically rewrite attendance. College policy must determine whether approved leave is excluded from the attendance denominator.
- Attendance currently counts Present and Late as attended; Excused is not counted.
- CSRF forms should be fully enabled in the production version. Flask-WTF is included; this starter uses basic HTML POST forms and must be upgraded with CSRF tokens before internet-facing deployment.
- Upload access is login-protected but not yet scoped by semester/batch. Review file type and access policy before production.
- Use a production WSGI server and HTTPS for deployment. Do not use Flask debug mode or the development secret key in production.
- Keep the `.env`, SQLite database and uploaded files out of source control. Back up the database securely.

## Suggested stages
1. Core login and roles.
2. Admin academic setup.
3. Attendance and reporting.
4. Leave workflow and audit controls.
5. Syllabus and quizzes.
6. CSRF, tests, semester filtering, edit/delete workflows, backups and production deployment.
