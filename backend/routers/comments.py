from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session, joinedload
from typing import Optional
import json

from database import get_db
import models, schemas
from auth import get_optional_user, decode_token
from websocket_manager import manager

router = APIRouter(tags=["comments"])


def build_comment(comment: models.Comment) -> dict:
    if comment.teacher:
        return {
            "id": comment.id,
            "post_id": comment.post_id,
            "content": comment.content,
            "created_at": comment.created_at.isoformat(),
            "author_name": comment.teacher.name,
            "author_type": "teacher",
            "author_id": comment.teacher.id,
        }
    elif comment.student:
        return {
            "id": comment.id,
            "post_id": comment.post_id,
            "content": comment.content,
            "created_at": comment.created_at.isoformat(),
            "author_name": comment.student.name,
            "author_type": "student",
            "author_id": comment.student.id,
        }
    return {}


@router.get("/posts/{post_id}/comments")
def get_comments(
    post_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    comments = (
        db.query(models.Comment)
        .options(joinedload(models.Comment.teacher), joinedload(models.Comment.student))
        .filter(models.Comment.post_id == post_id)
        .order_by(models.Comment.created_at.asc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return [build_comment(c) for c in comments]


@router.post("/posts/{post_id}/comments")
def add_comment(
    post_id: int,
    data: schemas.CommentCreate,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    uid = current_user.get("user_id")
    utype = current_user.get("user_type")

    comment = models.Comment(
        post_id=post_id,
        teacher_id=uid if utype in ("teacher", "admin") else None,
        student_id=uid if utype == "student" else None,
        content=data.content,
    )
    db.add(comment)
    if post.metrics:
        post.metrics.comment_count += 1
    db.flush()
    db.refresh(comment)
    if comment.teacher_id:
        comment.teacher = db.query(models.Teacher).filter(models.Teacher.id == comment.teacher_id).first()
    if comment.student_id:
        comment.student = db.query(models.Student).filter(models.Student.id == comment.student_id).first()
    db.commit()

    return build_comment(comment)


@router.websocket("/ws/comments/{post_id}")
async def websocket_comments(
    websocket: WebSocket,
    post_id: int,
    db: Session = Depends(get_db),
):
    await manager.connect(websocket, post_id)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "Invalid JSON"}))
                continue

            token = data.get("token", "")
            content = data.get("content", "").strip()

            if not content:
                continue

            if len(content) > 2000:
                await websocket.send_text(json.dumps({"error": "Comment too long"}))
                continue

            payload = decode_token(token) if token else {}
            if not payload:
                await websocket.send_text(json.dumps({"error": "Invalid token"}))
                continue

            uid = payload.get("user_id")
            utype = payload.get("user_type")

            post = db.query(models.Post).filter(models.Post.id == post_id).first()
            if not post:
                await websocket.send_text(json.dumps({"error": "Post not found"}))
                continue

            comment = models.Comment(
                post_id=post_id,
                teacher_id=uid if utype in ("teacher", "admin") else None,
                student_id=uid if utype == "student" else None,
                content=content,
            )
            db.add(comment)
            if post.metrics:
                post.metrics.comment_count += 1
            db.flush()
            db.refresh(comment)

            if comment.teacher_id:
                comment.teacher = db.query(models.Teacher).filter(models.Teacher.id == comment.teacher_id).first()
            if comment.student_id:
                comment.student = db.query(models.Student).filter(models.Student.id == comment.student_id).first()
            db.commit()

            msg = build_comment(comment)
            await manager.broadcast_to_post(post_id, msg)

    except WebSocketDisconnect:
        manager.disconnect(websocket, post_id)
