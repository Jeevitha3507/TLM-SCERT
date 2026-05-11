from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
import models
from auth import get_current_teacher, get_current_admin

router = APIRouter(prefix="/awards", tags=["awards"])

AWARD_TYPES = [
    "Best Innovator",
    "Most Active",
    "Student Impact",
    "District Champion",
    "SCERT Excellence",
]


class GiveAwardRequest(BaseModel):
    teacher_emis: str
    award_type: str
    award_reason: str
    academic_year: str


def _compute_score(teacher_id: int, db: Session) -> dict:
    posts = db.query(models.Post).filter(models.Post.teacher_id == teacher_id).all()
    total_posts = len(posts)
    total_likes = total_downloads = total_comments = 0
    months_seen: set = set()

    for p in posts:
        m = db.query(models.Metric).filter(models.Metric.post_id == p.id).first()
        if m:
            total_likes += m.like_count
            total_downloads += m.download_count
            total_comments += m.comment_count
        if p.created_at:
            months_seen.add(p.created_at.strftime("%Y-%m"))

    consistency_bonus = 20 if len(months_seen) >= 3 else 0

    teacher = db.query(models.Teacher).filter(models.Teacher.id == teacher_id).first()
    marks_score = 0
    if teacher:
        student_marks = db.query(models.StudentMark).filter(
            models.StudentMark.teacher_emis == teacher.emis_id
        ).all()
        for sm in student_marks:
            if 1 <= sm.improvement <= 5:
                marks_score += 5
            elif 6 <= sm.improvement <= 10:
                marks_score += 10
            elif sm.improvement > 10:
                marks_score += 20

    score = (
        total_posts * 10
        + total_likes * 5
        + total_downloads * 3
        + total_comments * 2
        + consistency_bonus
        + marks_score
    )
    return {
        "score": score,
        "total_posts": total_posts,
        "total_likes": total_likes,
        "total_downloads": total_downloads,
        "total_comments": total_comments,
        "consistency_bonus": consistency_bonus > 0,
        "marks_score": marks_score,
    }


@router.get("/leaderboard")
def get_leaderboard(
    current_user=Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    teachers = db.query(models.Teacher).filter(models.Teacher.is_admin == False).all()

    results = []
    for t in teachers:
        eng = _compute_score(t.id, db)
        results.append({
            "teacher_id": t.id,
            "emis_id": t.emis_id,
            "name": t.name,
            "district": t.district,
            "subject": t.subject,
            "school_name": t.school.name if t.school else None,
            **eng,
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:10]


@router.post("/give")
def give_award(
    payload: GiveAwardRequest,
    admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if payload.award_type not in AWARD_TYPES:
        raise HTTPException(status_code=400, detail="Invalid award type")

    teacher = db.query(models.Teacher).filter(
        models.Teacher.emis_id == payload.teacher_emis
    ).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    award = models.TeacherAward(
        teacher_emis=teacher.emis_id,
        teacher_name=teacher.name,
        school=teacher.school.name if teacher.school else None,
        district=teacher.district,
        award_type=payload.award_type,
        award_reason=payload.award_reason,
        awarded_by=admin["name"],
        awarded_date=datetime.utcnow(),
        academic_year=payload.academic_year,
    )
    db.add(award)
    db.commit()
    db.refresh(award)

    return {"id": award.id, "message": f"Award '{payload.award_type}' given to {teacher.name}"}


@router.get("/history")
def get_awards_history(
    award_type: Optional[str] = None,
    district: Optional[str] = None,
    academic_year: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    q = db.query(models.TeacherAward)

    if award_type:
        q = q.filter(models.TeacherAward.award_type == award_type)
    if district:
        q = q.filter(models.TeacherAward.district == district)
    if academic_year:
        q = q.filter(models.TeacherAward.academic_year == academic_year)

    total = q.count()
    awards = (
        q.order_by(models.TeacherAward.awarded_date.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return {
        "awards": [_award_dict(a) for a in awards],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/my")
def get_my_awards(
    current_user=Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    if current_user.get("is_admin"):
        return []

    awards = (
        db.query(models.TeacherAward)
        .filter(models.TeacherAward.teacher_emis == current_user["emis_id"])
        .order_by(models.TeacherAward.awarded_date.desc())
        .all()
    )
    return [_award_dict(a) for a in awards]


def _award_dict(a: models.TeacherAward) -> dict:
    return {
        "id": a.id,
        "teacher_emis": a.teacher_emis,
        "teacher_name": a.teacher_name,
        "school": a.school,
        "district": a.district,
        "award_type": a.award_type,
        "award_reason": a.award_reason,
        "awarded_by": a.awarded_by,
        "awarded_date": a.awarded_date.isoformat() if a.awarded_date else None,
        "academic_year": a.academic_year,
    }
