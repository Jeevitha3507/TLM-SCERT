import csv
import io
from typing import Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
import models, schemas
from auth import get_current_admin

router = APIRouter(prefix="/admin", tags=["admin"])


def calc_engagement(views: int, likes: int, downloads: int, comments: int) -> float:
    return round(views * 1 + likes * 3 + downloads * 2 + comments * 2, 2)


@router.get("/metrics")
def overall_metrics(
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return {
        "total_teachers": db.query(models.Teacher).filter(models.Teacher.is_admin == False).count(),
        "total_students": db.query(models.Student).count(),
        "total_posts": db.query(models.Post).count(),
        "total_views": db.query(func.sum(models.Metric.view_count)).scalar() or 0,
        "total_likes": db.query(func.sum(models.Metric.like_count)).scalar() or 0,
        "total_downloads": db.query(func.sum(models.Metric.download_count)).scalar() or 0,
        "total_comments": db.query(func.sum(models.Metric.comment_count)).scalar() or 0,
    }


@router.get("/teachers")
def teacher_report(
    district: Optional[str] = None,
    subject: Optional[str] = None,
    grade: Optional[int] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    teachers_q = db.query(models.Teacher).filter(models.Teacher.is_admin == False)
    if district:
        teachers_q = teachers_q.filter(models.Teacher.district == district)
    if subject:
        teachers_q = teachers_q.filter(models.Teacher.subject == subject)

    teachers = teachers_q.all()
    results = []

    for t in teachers:
        posts_q = db.query(models.Post).filter(models.Post.teacher_id == t.id)
        if grade:
            posts_q = posts_q.filter(models.Post.grade == grade)
        posts = posts_q.all()

        total_views = sum(
            db.query(func.sum(models.Metric.view_count)).filter(
                models.Metric.post_id == p.id
            ).scalar() or 0 for p in posts
        )
        total_likes = sum(
            db.query(func.sum(models.Metric.like_count)).filter(
                models.Metric.post_id == p.id
            ).scalar() or 0 for p in posts
        )
        total_downloads = sum(
            db.query(func.sum(models.Metric.download_count)).filter(
                models.Metric.post_id == p.id
            ).scalar() or 0 for p in posts
        )
        total_comments = sum(
            db.query(func.sum(models.Metric.comment_count)).filter(
                models.Metric.post_id == p.id
            ).scalar() or 0 for p in posts
        )

        results.append({
            "teacher_id": t.id,
            "emis_id": t.emis_id,
            "name": t.name,
            "district": t.district,
            "subject": t.subject,
            "school_name": t.school.name if t.school else None,
            "total_posts": len(posts),
            "total_views": total_views,
            "total_likes": total_likes,
            "total_downloads": total_downloads,
            "total_comments": total_comments,
            "engagement_score": calc_engagement(total_views, total_likes, total_downloads, total_comments),
        })

    results.sort(key=lambda x: x["engagement_score"], reverse=True)
    total = len(results)
    paginated = results[(page - 1) * per_page: page * per_page]

    return {"teachers": paginated, "total": total, "page": page, "per_page": per_page}


@router.get("/export")
def export_csv(
    district: Optional[str] = None,
    subject: Optional[str] = None,
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    teachers_q = db.query(models.Teacher).filter(models.Teacher.is_admin == False)
    if district:
        teachers_q = teachers_q.filter(models.Teacher.district == district)
    if subject:
        teachers_q = teachers_q.filter(models.Teacher.subject == subject)

    teachers = teachers_q.all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "EMIS ID", "Name", "District", "Subject", "School", "UDISE Code",
        "Total Posts", "Total Views", "Total Likes", "Total Downloads",
        "Total Comments", "Engagement Score"
    ])

    for t in teachers:
        posts = db.query(models.Post).filter(models.Post.teacher_id == t.id).all()
        total_v = total_l = total_d = total_c = 0
        for p in posts:
            m = db.query(models.Metric).filter_by(post_id=p.id).first()
            if m:
                total_v += m.view_count
                total_l += m.like_count
                total_d += m.download_count
                total_c += m.comment_count

        writer.writerow([
            t.emis_id, t.name, t.district, t.subject or "",
            t.school.name if t.school else "",
            t.school.udise_code if t.school else "",
            len(posts), total_v, total_l, total_d, total_c,
            calc_engagement(total_v, total_l, total_d, total_c),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=tlm_report.csv"},
    )


@router.get("/districts")
def get_districts(_admin=Depends(get_current_admin), db: Session = Depends(get_db)):
    districts = db.query(models.Teacher.district).distinct().all()
    return [d[0] for d in districts]


@router.get("/subjects")
def get_subjects(_admin=Depends(get_current_admin), db: Session = Depends(get_db)):
    subjects = db.query(models.Teacher.subject).distinct().filter(models.Teacher.subject != None).all()
    return [s[0] for s in subjects]


@router.get("/deletions")
def get_deletion_logs(
    search: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    q = db.query(models.DeletionLog)

    if search:
        like = f"%{search}%"
        q = q.filter(
            models.DeletionLog.post_title.ilike(like) |
            models.DeletionLog.deleted_by_emis.ilike(like) |
            models.DeletionLog.deleted_by_name.ilike(like) |
            models.DeletionLog.deletion_reason.ilike(like)
        )

    if date_from:
        try:
            from_dt = datetime.strptime(date_from, "%Y-%m-%d")
            q = q.filter(models.DeletionLog.deleted_at >= from_dt)
        except ValueError:
            pass

    if date_to:
        try:
            to_dt = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
            q = q.filter(models.DeletionLog.deleted_at < to_dt)
        except ValueError:
            pass

    total = q.count()
    logs = q.order_by(models.DeletionLog.deleted_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "logs": [
            {
                "id": log.id,
                "post_id": log.post_id,
                "post_title": log.post_title,
                "deleted_by_emis": log.deleted_by_emis,
                "deleted_by_name": log.deleted_by_name,
                "deletion_reason": log.deletion_reason,
                "deleted_at": log.deleted_at.isoformat(),
            }
            for log in logs
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }
