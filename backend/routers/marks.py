import csv
import io
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session

from database import get_db
import models
from auth import get_current_teacher, get_current_admin, get_current_user

router = APIRouter(prefix="/marks", tags=["marks"])
admin_router = APIRouter(prefix="/admin/marks", tags=["admin-marks"])

EXAM_TYPES = [
    "Unit Test 1", "Unit Test 2", "Unit Test 3",
    "Half Yearly", "Annual", "Practice Test",
]


class AddMarkRequest(BaseModel):
    student_emis: str = Field(..., min_length=1, max_length=20)
    student_name: str = Field(..., min_length=1, max_length=200)
    school_udise: Optional[str] = None
    post_id: Optional[int] = None
    subject: str = Field(..., min_length=1, max_length=100)
    grade: int = Field(..., ge=1, le=12)
    exam_type: str = Field(..., min_length=1, max_length=100)
    before_mark: int = Field(..., ge=0, le=100)
    after_mark: int = Field(..., ge=0, le=100)
    academic_year: str = Field(..., min_length=4, max_length=20)

    @validator("exam_type")
    def validate_exam_type(cls, v):
        if v not in EXAM_TYPES:
            raise ValueError(f"Must be one of: {', '.join(EXAM_TYPES)}")
        return v


def _mark_dict(m: models.StudentMark) -> dict:
    return {
        "id": m.id,
        "student_emis": m.student_emis,
        "student_name": m.student_name,
        "school_udise": m.school_udise,
        "teacher_emis": m.teacher_emis,
        "post_id": m.post_id,
        "post_title": m.post.title if m.post else None,
        "subject": m.subject,
        "grade": m.grade,
        "exam_type": m.exam_type,
        "before_mark": m.before_mark,
        "after_mark": m.after_mark,
        "improvement": m.improvement,
        "recorded_by": m.recorded_by,
        "recorded_date": m.recorded_date.isoformat() if m.recorded_date else None,
        "academic_year": m.academic_year,
    }


# ──────────────────────────────────────────────────────────────────
# Teacher endpoints
# ──────────────────────────────────────────────────────────────────

@router.post("/add")
def add_mark(
    payload: AddMarkRequest,
    current_user=Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    if payload.post_id:
        post = db.query(models.Post).filter(models.Post.id == payload.post_id).first()
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

    mark = models.StudentMark(
        student_emis=payload.student_emis,
        student_name=payload.student_name,
        school_udise=payload.school_udise,
        teacher_emis=current_user["emis_id"],
        post_id=payload.post_id,
        subject=payload.subject,
        grade=payload.grade,
        exam_type=payload.exam_type,
        before_mark=payload.before_mark,
        after_mark=payload.after_mark,
        improvement=payload.after_mark - payload.before_mark,
        recorded_by=current_user["name"],
        academic_year=payload.academic_year,
    )
    db.add(mark)
    db.commit()
    db.refresh(mark)
    return _mark_dict(mark)


@router.get("/my-students")
def get_my_students_marks(
    subject: Optional[str] = None,
    grade: Optional[int] = None,
    academic_year: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    q = db.query(models.StudentMark).filter(
        models.StudentMark.teacher_emis == current_user["emis_id"]
    )
    if subject:
        q = q.filter(models.StudentMark.subject == subject)
    if grade:
        q = q.filter(models.StudentMark.grade == grade)
    if academic_year:
        q = q.filter(models.StudentMark.academic_year == academic_year)

    total = q.count()
    marks = (
        q.order_by(models.StudentMark.recorded_date.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return {"marks": [_mark_dict(m) for m in marks], "total": total, "page": page, "per_page": per_page}


@router.get("/post/{post_id}")
def get_post_marks_impact(
    post_id: int,
    db: Session = Depends(get_db),
):
    marks = db.query(models.StudentMark).filter(models.StudentMark.post_id == post_id).all()
    if not marks:
        return {"post_id": post_id, "total_students": 0, "students_improved": 0, "avg_improvement": 0.0}

    improved = [m for m in marks if m.improvement > 0]
    avg = round(sum(m.improvement for m in marks) / len(marks), 2)
    return {
        "post_id": post_id,
        "total_students": len(marks),
        "students_improved": len(improved),
        "avg_improvement": avg,
    }


@router.get("/my-posts")
def get_my_posts_for_marks(
    current_user=Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    posts = (
        db.query(models.Post)
        .filter(models.Post.teacher_id == current_user["user_id"])
        .order_by(models.Post.created_at.desc())
        .all()
    )
    return [{"id": p.id, "title": p.title, "subject": p.subject, "grade": p.grade} for p in posts]


@router.get("/post/{post_id}/chart-data")
def get_post_marks_chart_data(
    post_id: int,
    db: Session = Depends(get_db),
):
    marks = db.query(models.StudentMark).filter(models.StudentMark.post_id == post_id).all()
    if not marks:
        return {"chart_data": [], "total": 0, "avg_before": 0, "avg_after": 0}
    avg_before = round(sum(m.before_mark for m in marks) / len(marks), 1)
    avg_after = round(sum(m.after_mark for m in marks) / len(marks), 1)
    return {
        "chart_data": [
            {"period": "Before TLM", "marks": avg_before},
            {"period": "After TLM", "marks": avg_after},
        ],
        "total": len(marks),
        "avg_before": avg_before,
        "avg_after": avg_after,
    }


@router.get("/student/{emis}")
def get_student_marks(
    emis: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_type = current_user.get("user_type")
    if user_type == "student":
        if current_user.get("emis_number") != emis:
            raise HTTPException(status_code=403, detail="Access denied")
    elif user_type not in ("teacher", "admin"):
        raise HTTPException(status_code=403, detail="Access denied")

    marks = (
        db.query(models.StudentMark)
        .filter(models.StudentMark.student_emis == emis)
        .order_by(models.StudentMark.recorded_date.desc())
        .all()
    )
    return {
        "student_emis": emis,
        "student_name": marks[0].student_name if marks else None,
        "marks": [_mark_dict(m) for m in marks],
    }


# ──────────────────────────────────────────────────────────────────
# Admin endpoints
# ──────────────────────────────────────────────────────────────────

@admin_router.get("")
def get_all_marks(
    district: Optional[str] = None,
    subject: Optional[str] = None,
    grade: Optional[int] = None,
    academic_year: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    q = db.query(models.StudentMark)
    if district:
        teacher_emis_in_district = [
            t.emis_id for t in
            db.query(models.Teacher).filter(models.Teacher.district == district).all()
        ]
        q = q.filter(models.StudentMark.teacher_emis.in_(teacher_emis_in_district))
    if subject:
        q = q.filter(models.StudentMark.subject == subject)
    if grade:
        q = q.filter(models.StudentMark.grade == grade)
    if academic_year:
        q = q.filter(models.StudentMark.academic_year == academic_year)

    total = q.count()
    marks = (
        q.order_by(models.StudentMark.recorded_date.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    all_marks = db.query(models.StudentMark).all()
    total_students_tracked = len(set(m.student_emis for m in all_marks))
    avg_improvement = round(
        sum(m.improvement for m in all_marks) / len(all_marks), 2
    ) if all_marks else 0.0

    return {
        "marks": [_mark_dict(m) for m in marks],
        "total": total,
        "page": page,
        "per_page": per_page,
        "summary": {
            "total_students_tracked": total_students_tracked,
            "avg_improvement": avg_improvement,
        },
    }


@admin_router.get("/by-district")
def get_marks_by_district(
    admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    all_marks = db.query(models.StudentMark).all()
    teacher_district: dict = {}
    for t in db.query(models.Teacher).all():
        teacher_district[t.emis_id] = t.district

    agg: dict = {}
    for m in all_marks:
        dist = teacher_district.get(m.teacher_emis, "Unknown")
        if dist not in agg:
            agg[dist] = {"total_improvement": 0, "count": 0}
        agg[dist]["total_improvement"] += m.improvement
        agg[dist]["count"] += 1

    result = [
        {
            "district": d,
            "avg_improvement": round(v["total_improvement"] / v["count"], 2) if v["count"] else 0,
            "student_count": v["count"],
        }
        for d, v in agg.items()
    ]
    result.sort(key=lambda x: -x["avg_improvement"])
    return result


@admin_router.get("/improvement-stats")
def get_improvement_stats(
    admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    all_marks = db.query(models.StudentMark).all()
    no_change = sum(1 for m in all_marks if m.improvement <= 0)
    low = sum(1 for m in all_marks if 1 <= m.improvement <= 5)
    mid = sum(1 for m in all_marks if 6 <= m.improvement <= 10)
    high = sum(1 for m in all_marks if m.improvement > 10)
    return [
        {"name": "No Change / Decline", "value": no_change, "color": "#94a3b8"},
        {"name": "1–5 Marks",           "value": low,       "color": "#f59e0b"},
        {"name": "6–10 Marks",          "value": mid,       "color": "#22c55e"},
        {"name": "10+ Marks",           "value": high,      "color": "#c2185b"},
    ]


@admin_router.get("/export-csv")
def export_marks_csv(
    district: Optional[str] = None,
    subject: Optional[str] = None,
    grade: Optional[int] = None,
    academic_year: Optional[str] = None,
    admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    q = db.query(models.StudentMark)
    if district:
        teacher_emis_in_district = [
            t.emis_id for t in
            db.query(models.Teacher).filter(models.Teacher.district == district).all()
        ]
        q = q.filter(models.StudentMark.teacher_emis.in_(teacher_emis_in_district))
    if subject:
        q = q.filter(models.StudentMark.subject == subject)
    if grade:
        q = q.filter(models.StudentMark.grade == grade)
    if academic_year:
        q = q.filter(models.StudentMark.academic_year == academic_year)

    marks = q.order_by(models.StudentMark.recorded_date.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Student EMIS", "Student Name", "School UDISE",
        "Teacher EMIS", "Post ID", "Post Title", "Subject", "Grade", "Exam Type",
        "Before Mark", "After Mark", "Improvement",
        "Recorded By", "Recorded Date", "Academic Year",
    ])
    for m in marks:
        writer.writerow([
            m.id, m.student_emis, m.student_name, m.school_udise or "",
            m.teacher_emis, m.post_id or "",
            m.post.title if m.post else "",
            m.subject, m.grade, m.exam_type,
            m.before_mark, m.after_mark, m.improvement,
            m.recorded_by,
            m.recorded_date.strftime("%Y-%m-%d") if m.recorded_date else "",
            m.academic_year,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=student_marks.csv"},
    )
