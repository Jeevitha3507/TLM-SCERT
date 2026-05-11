from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class School(Base):
    __tablename__ = "schools"

    id = Column(Integer, primary_key=True, index=True)
    udise_code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    district = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    teachers = relationship("Teacher", back_populates="school")
    students = relationship("Student", back_populates="school")


class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    emis_id = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    password_hash = Column(String(255), nullable=False)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=True)
    district = Column(String(100), nullable=False)
    subject = Column(String(100))
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    school = relationship("School", back_populates="teachers")
    posts = relationship("Post", back_populates="teacher")
    comments = relationship("Comment", back_populates="teacher")
    likes = relationship("Like", back_populates="teacher")
    downloads = relationship("Download", back_populates="teacher")
    views = relationship("View", back_populates="teacher")


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    emis_number = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=True)
    grade = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    school = relationship("School", back_populates="students")
    comments = relationship("Comment", back_populates="student")
    views = relationship("View", back_populates="student")


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    title = Column(String(500), nullable=False)
    subject = Column(String(100), nullable=False)
    grade = Column(Integer, nullable=False)
    tlm_method = Column(Text)
    file_url = Column(String(500))
    file_type = Column(String(20))
    original_filename = Column(String(300))
    created_at = Column(DateTime, default=datetime.utcnow)

    teacher = relationship("Teacher", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    likes = relationship("Like", back_populates="post", cascade="all, delete-orphan")
    downloads = relationship("Download", back_populates="post", cascade="all, delete-orphan")
    views = relationship("View", back_populates="post", cascade="all, delete-orphan")
    metrics = relationship("Metric", back_populates="post", uselist=False, cascade="all, delete-orphan")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    post = relationship("Post", back_populates="comments")
    teacher = relationship("Teacher", back_populates="comments")
    student = relationship("Student", back_populates="comments")


class Like(Base):
    __tablename__ = "likes"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    post = relationship("Post", back_populates="likes")
    teacher = relationship("Teacher", back_populates="likes")


class Download(Base):
    __tablename__ = "downloads"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    post = relationship("Post", back_populates="downloads")
    teacher = relationship("Teacher", back_populates="downloads")


class View(Base):
    __tablename__ = "views"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    post = relationship("Post", back_populates="views")
    teacher = relationship("Teacher", back_populates="views")
    student = relationship("Student", back_populates="views")


class Metric(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), unique=True, nullable=False)
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    download_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    post = relationship("Post", back_populates="metrics")


class DeletionLog(Base):
    __tablename__ = "deletion_logs"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, nullable=False, index=True)
    post_title = Column(String(500), nullable=False)
    deleted_by_emis = Column(String(20), nullable=False)
    deleted_by_name = Column(String(200), nullable=False)
    deletion_reason = Column(Text, nullable=False)
    deleted_at = Column(DateTime, default=datetime.utcnow)


class LoginAttempt(Base):
    __tablename__ = "login_attempts"

    id = Column(Integer, primary_key=True, index=True)
    emis_id = Column(String(20), nullable=False, index=True)
    ip_address = Column(String(45), nullable=False)
    success = Column(Boolean, nullable=False, default=False)
    attempted_at = Column(DateTime, default=datetime.utcnow)


class SecurityLog(Base):
    __tablename__ = "security_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    emis_id = Column(String(20), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class StudentMark(Base):
    __tablename__ = "student_marks"

    id = Column(Integer, primary_key=True, index=True)
    student_emis = Column(String(20), nullable=False, index=True)
    student_name = Column(String(200), nullable=False)
    school_udise = Column(String(20), nullable=True)
    teacher_emis = Column(String(20), nullable=False, index=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="SET NULL"), nullable=True)
    subject = Column(String(100), nullable=False)
    grade = Column(Integer, nullable=False)
    exam_type = Column(String(100), nullable=False)
    before_mark = Column(Integer, nullable=False)
    after_mark = Column(Integer, nullable=False)
    improvement = Column(Integer, nullable=False)
    recorded_by = Column(String(200), nullable=False)
    recorded_date = Column(DateTime, default=datetime.utcnow)
    academic_year = Column(String(20), nullable=False)

    post = relationship("Post", backref="student_marks")


class EmisExamMark(Base):
    __tablename__ = "emis_exam_marks"

    id = Column(Integer, primary_key=True, index=True)
    student_emis = Column(String(20), nullable=False, index=True)
    student_name = Column(String(200), nullable=False)
    grade = Column(Integer, nullable=False)
    section = Column(String(5), nullable=True)
    district = Column(String(100), nullable=True)
    school_name = Column(String(200), nullable=True)
    subject = Column(String(100), nullable=False)
    exam_type = Column(String(50), nullable=False)
    exam_date = Column(DateTime, nullable=False)
    marks_obtained = Column(Integer, nullable=False)
    total_marks = Column(Integer, nullable=False, default=100)
    academic_year = Column(String(20), nullable=False)


class TeacherAward(Base):
    __tablename__ = "teacher_awards"

    id = Column(Integer, primary_key=True, index=True)
    teacher_emis = Column(String(20), nullable=False, index=True)
    teacher_name = Column(String(200), nullable=False)
    school = Column(String(200), nullable=True)
    district = Column(String(100), nullable=False)
    award_type = Column(String(100), nullable=False)
    award_reason = Column(Text, nullable=False)
    awarded_by = Column(String(200), nullable=False)
    awarded_date = Column(DateTime, default=datetime.utcnow)
    academic_year = Column(String(20), nullable=False)
