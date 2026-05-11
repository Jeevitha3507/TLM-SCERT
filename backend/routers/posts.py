import os
import re
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload

from database import get_db
import models, schemas
from auth import get_current_teacher, get_optional_user, get_current_admin
from security_utils import log_security_event, get_client_ip

router = APIRouter(prefix="/posts", tags=["posts"])

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
MAX_VIDEO_BYTES = int(os.getenv("MAX_VIDEO_SIZE_MB", "100")) * 1024 * 1024
MAX_OTHER_BYTES = int(os.getenv("MAX_OTHER_SIZE_MB", "10")) * 1024 * 1024

# Only these extensions are permitted
ALLOWED_EXTENSIONS: dict[str, str] = {
    ".mp4": "video",
    ".mp3": "audio",
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
    ".pdf": "document",
}

_SAFE_FILENAME_RE = re.compile(r'^[\w\s.\-]+$')


def detect_file_type(filename: str) -> Optional[str]:
    ext = Path(filename).suffix.lower()
    return ALLOWED_EXTENSIONS.get(ext)


def safe_filename(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return f"{uuid.uuid4().hex}{ext}"


def validate_filename(filename: str) -> bool:
    name = Path(filename).name
    if not name:
        return False
    if '\x00' in filename or '..' in filename or '/' in filename or '\\' in filename:
        return False
    return bool(_SAFE_FILENAME_RE.match(name))


def build_post_response(post: models.Post, current_user: Optional[dict], db: Session) -> dict:
    liked = False
    if current_user:
        uid = current_user.get("user_id")
        utype = current_user.get("user_type")
        if utype in ("teacher", "admin"):
            liked = db.query(models.Like).filter_by(post_id=post.id, teacher_id=uid).first() is not None
        elif utype == "student":
            liked = db.query(models.Like).filter_by(post_id=post.id, student_id=uid).first() is not None

    school = None
    if post.teacher and post.teacher.school:
        s = post.teacher.school
        school = {"id": s.id, "udise_code": s.udise_code, "name": s.name, "district": s.district}

    metrics = {"view_count": 0, "like_count": 0, "download_count": 0, "comment_count": 0}
    if post.metrics:
        metrics = {
            "view_count": post.metrics.view_count,
            "like_count": post.metrics.like_count,
            "download_count": post.metrics.download_count,
            "comment_count": post.metrics.comment_count,
        }

    return {
        "id": post.id,
        "title": post.title,
        "subject": post.subject,
        "grade": post.grade,
        "tlm_method": post.tlm_method,
        "file_url": post.file_url,
        "file_type": post.file_type,
        "original_filename": post.original_filename,
        "created_at": post.created_at.isoformat(),
        "user_liked": liked,
        "metrics": metrics,
        "teacher": {
            "id": post.teacher.id,
            "emis_id": post.teacher.emis_id,
            "name": post.teacher.name,
            "district": post.teacher.district,
            "subject": post.teacher.subject,
            "is_admin": post.teacher.is_admin,
            "school": school,
        },
    }


@router.get("")
def list_posts(
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=50),
    subject: Optional[str] = None,
    grade: Optional[int] = None,
    district: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_user),
):
    q = db.query(models.Post).options(
        joinedload(models.Post.teacher).joinedload(models.Teacher.school),
        joinedload(models.Post.metrics),
    )
    if subject:
        q = q.filter(models.Post.subject == subject)
    if grade:
        q = q.filter(models.Post.grade == grade)
    if district:
        q = q.join(models.Teacher).filter(models.Teacher.district == district)
    if search:
        q = q.filter(models.Post.title.ilike(f"%{search}%"))

    total = q.count()
    posts = q.order_by(models.Post.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "posts": [build_post_response(p, current_user, db) for p in posts],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.post("")
async def create_post(
    request: Request,
    title: str = Form(...),
    subject: str = Form(...),
    grade: int = Form(...),
    tlm_method: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    current_teacher: dict = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    if not title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")

    ip = get_client_ip(request)
    file_url = None
    file_type = None
    original_filename = None

    if file and file.filename:
        if not validate_filename(file.filename):
            raise HTTPException(status_code=400, detail="Invalid filename: contains illegal characters")

        file_type = detect_file_type(file.filename)
        if not file_type:
            raise HTTPException(
                status_code=400,
                detail="File type not allowed. Permitted: mp4, mp3, jpg, jpeg, png, pdf",
            )

        max_size = MAX_VIDEO_BYTES if file_type == "video" else MAX_OTHER_BYTES
        contents = await file.read()
        if len(contents) > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Max {max_size // (1024 * 1024)} MB for {file_type}",
            )

        safe_name = safe_filename(file.filename)
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        save_path = os.path.join(UPLOAD_DIR, safe_name)
        with open(save_path, "wb") as f:
            f.write(contents)

        file_url = f"/uploads/{safe_name}"
        original_filename = file.filename

        log_security_event(
            db, "file_upload",
            current_teacher.get("emis_id"), ip,
            f"file={original_filename} type={file_type} size={len(contents)}",
        )

    teacher_id = current_teacher.get("user_id")
    teacher_type = current_teacher.get("user_type", "teacher")

    post = models.Post(
        teacher_id=teacher_id,
        title=title.strip(),
        subject=subject,
        grade=grade,
        tlm_method=tlm_method,
        file_url=file_url,
        file_type=file_type,
        original_filename=original_filename,
    )
    db.add(post)
    db.flush()

    metric = models.Metric(post_id=post.id)
    db.add(metric)
    db.commit()
    db.refresh(post)

    return build_post_response(post, {"user_id": teacher_id, "user_type": teacher_type}, db)


@router.get("/{post_id}")
def get_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_user),
):
    post = db.query(models.Post).options(
        joinedload(models.Post.teacher).joinedload(models.Teacher.school),
        joinedload(models.Post.metrics),
    ).filter(models.Post.id == post_id).first()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if current_user:
        uid = current_user.get("user_id")
        utype = current_user.get("user_type")
        existing_view = db.query(models.View).filter_by(
            post_id=post_id,
            teacher_id=uid if utype in ("teacher", "admin") else None,
            student_id=uid if utype == "student" else None,
        ).first()
        if not existing_view:
            view = models.View(
                post_id=post_id,
                teacher_id=uid if utype in ("teacher", "admin") else None,
                student_id=uid if utype == "student" else None,
            )
            db.add(view)
            if post.metrics:
                post.metrics.view_count += 1
            db.commit()
            db.refresh(post)

    return build_post_response(post, current_user, db)


@router.post("/{post_id}/like")
def toggle_like(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_optional_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    uid = current_user.get("user_id")
    utype = current_user.get("user_type")

    if utype in ("teacher", "admin"):
        existing = db.query(models.Like).filter_by(post_id=post_id, teacher_id=uid).first()
        if existing:
            db.delete(existing)
            if post.metrics:
                post.metrics.like_count = max(0, post.metrics.like_count - 1)
            db.commit()
            return {"liked": False, "like_count": post.metrics.like_count if post.metrics else 0}
        like = models.Like(post_id=post_id, teacher_id=uid)
    else:
        existing = db.query(models.Like).filter_by(post_id=post_id, student_id=uid).first()
        if existing:
            db.delete(existing)
            if post.metrics:
                post.metrics.like_count = max(0, post.metrics.like_count - 1)
            db.commit()
            return {"liked": False, "like_count": post.metrics.like_count if post.metrics else 0}
        like = models.Like(post_id=post_id, student_id=uid)

    db.add(like)
    if post.metrics:
        post.metrics.like_count += 1
    db.commit()
    return {"liked": True, "like_count": post.metrics.like_count if post.metrics else 1}


@router.delete("/{post_id}")
def delete_post(
    post_id: int,
    body: schemas.DeletePostRequest,
    db: Session = Depends(get_db),
    current_teacher: dict = Depends(get_current_teacher),
):
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Teachers can only delete their own posts; admins can delete any post
    if not current_teacher.get("is_admin") and post.teacher_id != current_teacher.get("user_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own posts",
        )

    log = models.DeletionLog(
        post_id=post.id,
        post_title=post.title,
        deleted_by_emis=current_teacher.get("emis_id", ""),
        deleted_by_name=current_teacher.get("name", ""),
        deletion_reason=body.reason,
    )
    db.add(log)

    log_security_event(
        db, "post_delete",
        current_teacher.get("emis_id"), None,
        f"post_id={post.id} title={post.title!r} reason={body.reason!r}",
    )

    if post.file_url:
        file_path = os.path.join(UPLOAD_DIR, os.path.basename(post.file_url))
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass

    db.delete(post)
    db.commit()

    return {"message": "Post deleted successfully", "post_id": post_id}


@router.post("/{post_id}/download")
def record_download(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_user),
):
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    uid = current_user.get("user_id") if current_user else None
    utype = current_user.get("user_type") if current_user else None

    download = models.Download(
        post_id=post_id,
        teacher_id=uid if utype in ("teacher", "admin") else None,
        student_id=uid if utype == "student" else None,
    )
    db.add(download)
    if post.metrics:
        post.metrics.download_count += 1
    db.commit()

    return {"download_count": post.metrics.download_count if post.metrics else 1}
