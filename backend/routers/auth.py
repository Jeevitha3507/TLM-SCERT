from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import os

from database import get_db
import models, schemas
from auth import (
    verify_password,
    create_access_token,
    get_current_user,
)
from security_utils import log_security_event, get_client_ip

router = APIRouter(prefix="/auth", tags=["auth"])

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def _is_locked_out(db: Session, emis_id: str) -> bool:
    cutoff = datetime.utcnow() - timedelta(minutes=LOCKOUT_MINUTES)
    count = (
        db.query(models.LoginAttempt)
        .filter(
            models.LoginAttempt.emis_id == emis_id,
            models.LoginAttempt.success == False,
            models.LoginAttempt.attempted_at >= cutoff,
        )
        .count()
    )
    return count >= MAX_FAILED_ATTEMPTS


@router.post("/teacher/login", response_model=schemas.TokenResponse)
def teacher_login(
    request: Request,
    data: schemas.TeacherLogin,
    db: Session = Depends(get_db),
):
    ip = get_client_ip(request)

    if _is_locked_out(db, data.emis_id):
        log_security_event(
            db, "login_blocked", data.emis_id, ip,
            "Blocked: exceeded 5 failed attempts in 15 minutes",
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Account temporarily locked. Try again in 15 minutes.",
        )

    teacher = db.query(models.Teacher).filter(
        models.Teacher.emis_id == data.emis_id
    ).first()

    if not teacher or not verify_password(data.password, teacher.password_hash):
        db.add(models.LoginAttempt(emis_id=data.emis_id, ip_address=ip, success=False))
        db.commit()
        log_security_event(db, "login_failure", data.emis_id, ip, "Invalid credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid EMIS ID or password",
        )

    db.add(models.LoginAttempt(emis_id=data.emis_id, ip_address=ip, success=True))
    db.commit()
    log_security_event(db, "login_success", data.emis_id, ip, f"Login: {teacher.name}")

    token = create_access_token({
        "user_id": teacher.id,
        "user_type": "admin" if teacher.is_admin else "teacher",
        "emis_id": teacher.emis_id,
        "name": teacher.name,
        "is_admin": teacher.is_admin,
    })

    return schemas.TokenResponse(
        access_token=token,
        user_type="admin" if teacher.is_admin else "teacher",
        user_id=teacher.id,
        name=teacher.name,
        is_admin=teacher.is_admin,
    )


@router.post("/student/view", response_model=schemas.TokenResponse)
def student_view(
    data: schemas.StudentView,
    db: Session = Depends(get_db),
):
    student = db.query(models.Student).filter(
        models.Student.emis_number == data.emis_number
    ).first()

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student EMIS number not found",
        )

    token = create_access_token({
        "user_id": student.id,
        "user_type": "student",
        "emis_number": student.emis_number,
        "name": student.name,
        "is_admin": False,
    })

    return schemas.TokenResponse(
        access_token=token,
        user_type="student",
        user_id=student.id,
        name=student.name,
        is_admin=False,
    )


@router.get("/me")
def get_me(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.get("user_type") in ("teacher", "admin"):
        teacher = db.query(models.Teacher).filter(
            models.Teacher.id == current_user["user_id"]
        ).first()
        if not teacher:
            raise HTTPException(status_code=404, detail="Not found")

        school = None
        if teacher.school:
            school = {
                "id": teacher.school.id,
                "name": teacher.school.name,
                "udise_code": teacher.school.udise_code,
                "district": teacher.school.district,
            }

        return {
            "user_type": current_user["user_type"],
            "user_id": teacher.id,
            "emis_id": teacher.emis_id,
            "name": teacher.name,
            "district": teacher.district,
            "subject": teacher.subject,
            "school": school,
            "is_admin": teacher.is_admin,
        }

    if current_user.get("user_type") == "student":
        student = db.query(models.Student).filter(
            models.Student.id == current_user["user_id"]
        ).first()
        if not student:
            raise HTTPException(status_code=404, detail="Not found")

        return {
            "user_type": "student",
            "user_id": student.id,
            "emis_number": student.emis_number,
            "name": student.name,
            "grade": student.grade,
            "is_admin": False,
        }

    raise HTTPException(status_code=400, detail="Unknown user type")
