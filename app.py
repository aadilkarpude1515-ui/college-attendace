import os
from datetime import datetime, date
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-this-secret")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(app.instance_path, "college.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
os.makedirs(app.instance_path, exist_ok=True)
os.makedirs(os.path.join(app.root_path, "uploads"), exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# ---------------------------- Database models ----------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, teacher, student
    active = db.Column(db.Boolean, default=True, nullable=False)
    must_change_password = db.Column(db.Boolean, default=True, nullable=False)
    student_profile = db.relationship("Student", backref="user", uselist=False, cascade="all, delete-orphan")
    teacher_profile = db.relationship("Teacher", backref="user", uselist=False, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Batch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    department = db.Column(db.String(100), default="Computer Engineering")
    students = db.relationship("Student", backref="batch", lazy=True)

class Semester(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, nullable=False, unique=True)
    academic_year = db.Column(db.String(20), default="2026-2027")

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(40), unique=True, nullable=False)
    prn = db.Column(db.String(40), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey("batch.id"), nullable=False)
    current_semester_id = db.Column(db.Integer, db.ForeignKey("semester.id"), nullable=True)

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.String(40), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    semester_id = db.Column(db.Integer, db.ForeignKey("semester.id"), nullable=False)
    semester = db.relationship("Semester", backref="subjects")

class TeacherAssignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teacher.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subject.id"), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey("batch.id"), nullable=False)
    teacher = db.relationship("Teacher", backref="assignments")
    subject = db.relationship("Subject")
    batch = db.relationship("Batch")
    __table_args__ = (db.UniqueConstraint("teacher_id", "subject_id", "batch_id"),)

class ClassTeacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teacher.id"), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey("batch.id"), nullable=False)
    teacher = db.relationship("Teacher", backref="class_teacher_assignments")
    batch = db.relationship("Batch")
    __table_args__ = (db.UniqueConstraint("teacher_id", "batch_id"),)

class AttendanceSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subject.id"), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey("batch.id"), nullable=False)
    session_date = db.Column(db.Date, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("teacher.id"), nullable=False)
    subject = db.relationship("Subject")
    batch = db.relationship("Batch")
    __table_args__ = (db.UniqueConstraint("subject_id", "batch_id", "session_date"),)

class AttendanceRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("attendance_session.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Absent")
    marked_by = db.Column(db.Integer, db.ForeignKey("teacher.id"), nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    session = db.relationship("AttendanceSession", backref=db.backref("records", cascade="all, delete-orphan"))
    student = db.relationship("Student")
    __table_args__ = (db.UniqueConstraint("session_id", "student_id"),)

class LeaveApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="Pending", nullable=False)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("teacher.id"), nullable=True)
    review_comment = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    student = db.relationship("Student")
    reviewer = db.relationship("Teacher")

class Syllabus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subject.id"), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, default="")
    filename = db.Column(db.String(255), default="")
    subject = db.relationship("Subject")

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subject.id"), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey("batch.id"), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teacher.id"), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    instructions = db.Column(db.Text, default="")
    deadline = db.Column(db.DateTime, nullable=True)
    subject = db.relationship("Subject")
    batch = db.relationship("Batch")
    questions = db.relationship("QuizQuestion", backref="quiz", cascade="all, delete-orphan")
    attempts = db.relationship("QuizAttempt", backref="quiz", cascade="all, delete-orphan")

class QuizQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quiz.id"), nullable=False)
    prompt = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(250), nullable=False)
    option_b = db.Column(db.String(250), nullable=False)
    option_c = db.Column(db.String(250), nullable=False)
    option_d = db.Column(db.String(250), nullable=False)
    correct_option = db.Column(db.String(1), nullable=False)
    marks = db.Column(db.Integer, default=1)

class QuizAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quiz.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    score = db.Column(db.Integer, nullable=False, default=0)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    student = db.relationship("Student")
    __table_args__ = (db.UniqueConstraint("quiz_id", "student_id"),)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    detail = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            if current_user.must_change_password and request.endpoint not in ("change_password", "logout", "static"):
                return redirect(url_for("change_password"))
            return fn(*args, **kwargs)
        return wrapped
    return decorator

def log_action(action, detail=""):
    db.session.add(AuditLog(actor_user_id=current_user.id if current_user.is_authenticated else None,
                            action=action, detail=detail))

def current_student():
    return current_user.student_profile

def current_teacher():
    return current_user.teacher_profile

def teacher_can_access(teacher, subject_id, batch_id):
    return TeacherAssignment.query.filter_by(teacher_id=teacher.id, subject_id=subject_id, batch_id=batch_id).first() is not None

@app.context_processor
def inject_helpers():
    return {"today": date.today()}

# ---------------------------- Authentication ----------------------------
@app.route("/")
def index():
    if current_user.is_authenticated:
        if current_user.role == "admin": return redirect(url_for("admin_dashboard"))
        if current_user.role == "teacher": return redirect(url_for("teacher_dashboard"))
        return redirect(url_for("student_dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username, active=True).first()
        if user and user.check_password(password):
            login_user(user)
            if user.must_change_password:
                return redirect(url_for("change_password"))
            flash("Welcome back!", "success")
            return redirect(url_for("index"))
        flash("Invalid credentials or inactive account.", "error")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "success")
    return redirect(url_for("login"))

@app.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        old = request.form.get("current_password", "")
        new = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")
        new_id = request.form.get("new_username", "").strip()
        if not current_user.check_password(old):
            flash("Current password is incorrect.", "error")
        elif len(new) < 10 or not any(c.isalpha() for c in new) or not any(c.isdigit() for c in new):
            flash("Use at least 10 characters including a letter and a number.", "error")
        elif new != confirm:
            flash("New passwords do not match.", "error")
        elif new_id and new_id != current_user.username and User.query.filter_by(username=new_id).first():
            flash("That login ID is already in use.", "error")
        else:
            if new_id: current_user.username = new_id
            current_user.set_password(new)
            current_user.must_change_password = False
            log_action("credentials_changed", "User changed login credentials")
            db.session.commit()
            flash("Credentials updated.", "success")
            return redirect(url_for("index"))
    return render_template("change_password.html")

# ---------------------------- Student routes ----------------------------
@app.route("/student")
@role_required("student")
def student_dashboard():
    student = current_student()
    sessions = AttendanceSession.query.join(AttendanceRecord).filter(AttendanceRecord.student_id == student.id).all()
    records = AttendanceRecord.query.filter_by(student_id=student.id).all()
    total = len(records)
    attended = sum(1 for r in records if r.status in ("Present", "Late"))
    overall = round(attended * 100 / total, 1) if total else 0
    subjects = Subject.query.join(AttendanceSession).join(AttendanceRecord).filter(AttendanceRecord.student_id == student.id).distinct().all()
    stats = []
    for subject in subjects:
        recs = AttendanceRecord.query.join(AttendanceSession).filter(
            AttendanceRecord.student_id == student.id,
            AttendanceSession.subject_id == subject.id).all()
        n = len(recs); a = sum(1 for r in recs if r.status in ("Present", "Late"))
        stats.append({"subject": subject, "attended": a, "total": n, "pct": round(a*100/n,1) if n else 0})
    leaves = LeaveApplication.query.filter_by(student_id=student.id).order_by(LeaveApplication.created_at.desc()).all()
    quizzes = Quiz.query.filter_by(batch_id=student.batch_id).order_by(Quiz.id.desc()).all()
    attempts = {a.quiz_id: a for a in QuizAttempt.query.filter_by(student_id=student.id).all()}
    return render_template("student.html", student=student, overall=overall, attended=attended,
                           total=total, stats=stats, leaves=leaves, quizzes=quizzes, attempts=attempts)

@app.route("/student/leave", methods=["POST"])
@role_required("student")
def apply_leave():
    try:
        start = date.fromisoformat(request.form.get("start_date", ""))
        end = date.fromisoformat(request.form.get("end_date", ""))
    except ValueError:
        flash("Please select valid dates.", "error"); return redirect(url_for("student_dashboard"))
    reason = request.form.get("reason", "").strip()
    if end < start or not reason:
        flash("End date must not precede start date, and reason is required.", "error")
    else:
        db.session.add(LeaveApplication(student_id=current_student().id, start_date=start, end_date=end, reason=reason))
        log_action("leave_applied", f"Student {current_student().student_id} applied for leave")
        db.session.commit()
        flash("Leave application submitted.", "success")
    return redirect(url_for("student_dashboard"))

@app.route("/student/syllabus")
@role_required("student")
def student_syllabus():
    student = current_student()
    sem_ids = [s.id for s in Semester.query.all()]
    items = Syllabus.query.join(Subject).filter(Subject.semester_id.in_(sem_ids)).all() if sem_ids else []
    return render_template("syllabus.html", items=items, student=student)

@app.route("/student/quiz/<int:quiz_id>", methods=["GET", "POST"])
@role_required("student")
def take_quiz(quiz_id):
    student = current_student()
    quiz = db.get_or_404(Quiz, quiz_id)
    if quiz.batch_id != student.batch_id: abort(403)
    if quiz.deadline and datetime.now() > quiz.deadline:
        flash("This quiz deadline has passed.", "error"); return redirect(url_for("student_dashboard"))
    existing = QuizAttempt.query.filter_by(quiz_id=quiz.id, student_id=student.id).first()
    if existing:
        flash(f"You have already submitted this quiz. Score: {existing.score}", "success")
        return redirect(url_for("student_dashboard"))
    if request.method == "POST":
        score = 0
        for q in quiz.questions:
            if request.form.get(str(q.id), "").upper() == q.correct_option:
                score += q.marks
        db.session.add(QuizAttempt(quiz_id=quiz.id, student_id=student.id, score=score))
        log_action("quiz_submitted", f"Quiz {quiz.id} submitted by student {student.student_id}")
        db.session.commit()
        flash(f"Quiz submitted. Your score is {score}.", "success")
        return redirect(url_for("student_dashboard"))
    return render_template("take_quiz.html", quiz=quiz)

# ---------------------------- Teacher routes ----------------------------
@app.route("/teacher")
@role_required("teacher")
def teacher_dashboard():
    teacher = current_teacher()
    assignments = TeacherAssignment.query.filter_by(teacher_id=teacher.id).all()
    pending = []
    for ct in ClassTeacher.query.filter_by(teacher_id=teacher.id).all():
        batch_student_ids = [s.id for s in Student.query.filter_by(batch_id=ct.batch_id).all()]
        pending.extend(LeaveApplication.query.filter(LeaveApplication.status == "Pending",
                      LeaveApplication.student_id.in_(batch_student_ids)).all() if batch_student_ids else [])
    quizzes = Quiz.query.filter_by(teacher_id=teacher.id).all()
    return render_template("teacher.html", teacher=teacher, assignments=assignments, pending=pending, quizzes=quizzes)

@app.route("/teacher/attendance", methods=["GET", "POST"])
@role_required("teacher")
def mark_attendance():
    teacher = current_teacher()
    assignments = TeacherAssignment.query.filter_by(teacher_id=teacher.id).all()
    if request.method == "POST":
        try:
            subject_id = int(request.form["subject_id"]); batch_id = int(request.form["batch_id"])
            session_date = date.fromisoformat(request.form["session_date"])
        except (ValueError, KeyError):
            flash("Invalid subject, batch, or date.", "error"); return redirect(url_for("mark_attendance"))
        if not teacher_can_access(teacher, subject_id, batch_id): abort(403)
        session = AttendanceSession.query.filter_by(subject_id=subject_id, batch_id=batch_id, session_date=session_date).first()
        if not session:
            session = AttendanceSession(subject_id=subject_id, batch_id=batch_id, session_date=session_date, created_by=teacher.id)
            db.session.add(session); db.session.flush()
        students = Student.query.filter_by(batch_id=batch_id).order_by(Student.name).all()
        for student in students:
            status = request.form.get(f"status_{student.id}", "Absent")
            if status not in ("Present", "Absent", "Late", "Excused"): status = "Absent"
            record = AttendanceRecord.query.filter_by(session_id=session.id, student_id=student.id).first()
            if record:
                record.status = status; record.marked_by = teacher.id
            else:
                db.session.add(AttendanceRecord(session_id=session.id, student_id=student.id, status=status, marked_by=teacher.id))
        log_action("attendance_saved", f"Subject {subject_id}, batch {batch_id}, date {session_date}")
        db.session.commit()
        flash("Attendance saved.", "success")
        return redirect(url_for("teacher_dashboard"))
    return render_template("attendance.html", assignments=assignments)

@app.route("/teacher/leave/<int:leave_id>", methods=["POST"])
@role_required("teacher")
def review_leave(leave_id):
    teacher = current_teacher()
    leave = db.get_or_404(LeaveApplication, leave_id)
    class_assignment = ClassTeacher.query.filter_by(teacher_id=teacher.id, batch_id=leave.student.batch_id).first()
    if not class_assignment: abort(403)
    status = request.form.get("status")
    if status not in ("Approved", "Rejected"): abort(400)
    leave.status = status
    leave.reviewed_by = teacher.id
    leave.review_comment = request.form.get("comment", "").strip()
    log_action("leave_reviewed", f"Leave {leave.id}: {status}")
    db.session.commit()
    flash(f"Leave {status.lower()}.", "success")
    return redirect(url_for("teacher_dashboard"))

@app.route("/teacher/quiz", methods=["GET", "POST"])
@role_required("teacher")
def create_quiz():
    teacher = current_teacher()
    assignments = TeacherAssignment.query.filter_by(teacher_id=teacher.id).all()
    if request.method == "POST":
        try:
            assignment_id = int(request.form["assignment_id"])
            assignment = TeacherAssignment.query.filter_by(id=assignment_id, teacher_id=teacher.id).first_or_404()
            title = request.form.get("title", "").strip()
            prompt = request.form.get("question", "").strip()
            options = [request.form.get(f"option_{x}", "").strip() for x in "ABCD"]
            correct = request.form.get("correct", "A").upper()
            marks = max(1, min(100, int(request.form.get("marks", "1"))))
            if not title or not prompt or any(not x for x in options) or correct not in "ABCD":
                raise ValueError()
        except (ValueError, KeyError):
            flash("Fill in the quiz title, question, all four options, and correct answer.", "error")
            return redirect(url_for("create_quiz"))
        quiz = Quiz(subject_id=assignment.subject_id, batch_id=assignment.batch_id, teacher_id=teacher.id,
                    title=title, instructions=request.form.get("instructions", "").strip())
        db.session.add(quiz); db.session.flush()
        db.session.add(QuizQuestion(quiz_id=quiz.id, prompt=prompt, option_a=options[0], option_b=options[1],
                                    option_c=options[2], option_d=options[3], correct_option=correct, marks=marks))
        log_action("quiz_created", f"Quiz {title}")
        db.session.commit()
        flash("Quiz created. This version supports one multiple-choice question per quiz; multi-question editing can be added next.", "success")
        return redirect(url_for("teacher_dashboard"))
    return render_template("create_quiz.html", assignments=assignments)

# ---------------------------- Admin routes ----------------------------
@app.route("/admin")
@role_required("admin")
def admin_dashboard():
    return render_template("admin.html", students=Student.query.order_by(Student.name).all(),
        teachers=Teacher.query.order_by(Teacher.name).all(), batches=Batch.query.all(),
        semesters=Semester.query.order_by(Semester.number).all(), subjects=Subject.query.all(),
        assignments=TeacherAssignment.query.all(), class_teachers=ClassTeacher.query.all(),
        users=User.query.order_by(User.role, User.username).all(), logs=AuditLog.query.order_by(AuditLog.created_at.desc()).limit(30).all())

@app.route("/admin/create", methods=["POST"])
@role_required("admin")
def admin_create():
    kind = request.form.get("kind")
    try:
        if kind == "batch":
            name = request.form["name"].strip()
            if not name: raise ValueError()
            db.session.add(Batch(name=name, department=request.form.get("department", "Computer Engineering")))
        elif kind == "semester":
            db.session.add(Semester(number=int(request.form["number"]), academic_year=request.form.get("academic_year", "2026-2027")))
        elif kind == "student":
            username = request.form["student_id"].strip(); prn = request.form["prn"].strip(); name = request.form["name"].strip()
            batch_id = int(request.form["batch_id"])
            if not all([username, prn, name]): raise ValueError()
            user = User(username=username, role="student", must_change_password=True); user.set_password(prn)
            db.session.add(user); db.session.flush()
            db.session.add(Student(student_id=username, prn=prn, name=name, batch_id=batch_id,
                                   current_semester_id=int(request.form["semester_id"]) if request.form.get("semester_id") else None,
                                   user_id=user.id))
        elif kind == "teacher":
            username = request.form["teacher_id"].strip(); name = request.form["name"].strip()
            if not username or not name: raise ValueError()
            initial = request.form.get("initial_password", "").strip() or ("Temp-" + os.urandom(4).hex() + "A9")
            user = User(username=username, role="teacher", must_change_password=True); user.set_password(initial)
            db.session.add(user); db.session.flush()
            db.session.add(Teacher(teacher_id=username, name=name, user_id=user.id))
            flash(f"Teacher created. Initial password: {initial} (share securely and ask teacher to change it).", "success")
        elif kind == "subject":
            db.session.add(Subject(code=request.form["code"].strip(), name=request.form["name"].strip(), semester_id=int(request.form["semester_id"])))
        elif kind == "assignment":
            db.session.add(TeacherAssignment(teacher_id=int(request.form["teacher_id"]), subject_id=int(request.form["subject_id"]), batch_id=int(request.form["batch_id"])))
        elif kind == "class_teacher":
            db.session.add(ClassTeacher(teacher_id=int(request.form["teacher_id"]), batch_id=int(request.form["batch_id"])))
        elif kind == "syllabus":
            subject = db.session.get(Subject, int(request.form["subject_id"]))
            title = request.form.get("title", "").strip()
            content = request.form.get("content", "").strip()
            upload = request.files.get("file")
            filename = ""
            if upload and upload.filename:
                safe = secure_filename(upload.filename)
                if safe:
                    filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{safe}"
                    upload.save(os.path.join(app.root_path, "uploads", filename))
            db.session.add(Syllabus(subject_id=subject.id, title=title, content=content, filename=filename))
        else:
            abort(400)
        log_action("admin_create", f"Created {kind}")
        db.session.commit()
        flash(f"{kind.replace('_',' ').title()} created.", "success")
    except (ValueError, KeyError, TypeError):
        db.session.rollback()
        flash("Invalid or incomplete form. Check the values and unique IDs.", "error")
    except Exception:
        db.session.rollback()
        flash("Could not create record. Check for duplicate IDs or invalid assignments.", "error")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/user/<int:user_id>/reset", methods=["POST"])
@role_required("admin")
def reset_user_password(user_id):
    user = db.get_or_404(User, user_id)
    new_password = request.form.get("new_password", "").strip()
    if len(new_password) < 10 or not any(c.isalpha() for c in new_password) or not any(c.isdigit() for c in new_password):
        flash("Reset password must be at least 10 characters and contain a letter and number.", "error")
    else:
        user.set_password(new_password); user.must_change_password = True
        log_action("password_reset", f"Reset credentials for user {user.username}")
        db.session.commit()
        flash("Password reset. User must change it at next login.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/user/<int:user_id>/toggle", methods=["POST"])
@role_required("admin")
def toggle_user(user_id):
    user = db.get_or_404(User, user_id)
    if user.id == current_user.id:
        flash("You cannot deactivate your own account.", "error")
    else:
        user.active = not user.active
        log_action("account_status_changed", f"{user.username}: active={user.active}")
        db.session.commit()
        flash("Account status updated.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/student/<int:student_id>/delete", methods=["POST"])
@role_required("admin")
def delete_student(student_id):
    student = db.get_or_404(Student, student_id)
    username = student.student_id
    # Keep audit integrity: deactivate account instead of destructive cascade delete.
    student.user.active = False
    log_action("student_deactivated", f"Student {username} deactivated; historical data retained")
    db.session.commit()
    flash("Student account deactivated; historical records retained for audit.", "success")
    return redirect(url_for("admin_dashboard"))

# ---------------------------- Syllabus file serving ----------------------------
@app.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    from flask import send_from_directory
    if current_user.role not in ("admin", "teacher", "student"): abort(403)
    return send_from_directory(os.path.join(app.root_path, "uploads"), filename, as_attachment=True)

# ---------------------------- Initial setup / development seed ----------------------------
@app.cli.command("init-db")
def init_db():
    """Create tables and a development admin account if one does not exist."""
    db.create_all()
    if not User.query.filter_by(role="admin").first():
        username = os.environ.get("INITIAL_ADMIN_ID", "admin")
        password = os.environ.get("INITIAL_ADMIN_PASSWORD", "admin123")
        user = User(username=username, role="admin", must_change_password=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print(f"Created admin account: {username}. Change its password immediately.")
    if not Batch.query.first():
        db.session.add(Batch(name="CSE-A", department="Computer Engineering"))
        db.session.commit()
    if not Semester.query.first():
        for n in range(1, 9): db.session.add(Semester(number=n, academic_year="2026-2027"))
        db.session.commit()
    print("Database initialized.")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(role="admin").first():
            admin_id = os.environ.get("INITIAL_ADMIN_ID", "admin")
            admin_pw = os.environ.get("INITIAL_ADMIN_PASSWORD", "admin123")
            admin = User(username=admin_id, role="admin", must_change_password=True)
            admin.set_password(admin_pw)
            db.session.add(admin)
            db.session.commit()
            print(f"Development admin created: ID={admin_id}; password={admin_pw}. Change immediately.")
    app.run(debug=True)

@app.route("/teacher/roster")
@role_required("teacher")
def teacher_roster():
    teacher = current_teacher()
    try: assignment_id = int(request.args.get("assignment_id", ""))
    except ValueError: abort(400)
    assignment = TeacherAssignment.query.filter_by(id=assignment_id, teacher_id=teacher.id).first_or_404()
    students = Student.query.filter_by(batch_id=assignment.batch_id).order_by(Student.name).all()
    from flask import jsonify
    return jsonify([{"id": s.id, "name": s.name, "student_id": s.student_id} for s in students])

