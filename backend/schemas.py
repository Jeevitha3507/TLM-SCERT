from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime


class TeacherLogin(BaseModel):
    emis_id: str = Field(..., min_length=1, max_length=20)
    password: str = Field(..., min_length=1)


class StudentView(BaseModel):
    emis_number: str = Field(..., min_length=1, max_length=20)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_type: str
    user_id: int
    name: str
    is_admin: bool = False


class SchoolResponse(BaseModel):
    id: int
    udise_code: str
    name: str
    district: str

    class Config:
        from_attributes = True


class TeacherResponse(BaseModel):
    id: int
    emis_id: str
    name: str
    district: str
    subject: Optional[str]
    school: Optional[SchoolResponse]
    is_admin: bool

    class Config:
        from_attributes = True


class StudentResponse(BaseModel):
    id: int
    emis_number: str
    name: str
    grade: Optional[int]
    school: Optional[SchoolResponse]

    class Config:
        from_attributes = True


class MetricResponse(BaseModel):
    view_count: int = 0
    like_count: int = 0
    download_count: int = 0
    comment_count: int = 0

    class Config:
        from_attributes = True


class PostBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    subject: str = Field(..., min_length=1, max_length=100)
    grade: int = Field(..., ge=1, le=12)
    tlm_method: Optional[str] = None


class PostResponse(BaseModel):
    id: int
    title: str
    subject: str
    grade: int
    tlm_method: Optional[str]
    file_url: Optional[str]
    file_type: Optional[str]
    original_filename: Optional[str]
    created_at: datetime
    teacher: TeacherResponse
    metrics: Optional[MetricResponse]
    user_liked: bool = False

    class Config:
        from_attributes = True


class PostList(BaseModel):
    posts: List[PostResponse]
    total: int
    page: int
    per_page: int


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)

    @validator('content')
    def sanitize_content(cls, v):
        return v.strip()


class CommentResponse(BaseModel):
    id: int
    post_id: int
    content: str
    created_at: datetime
    author_name: str
    author_type: str
    author_id: int

    class Config:
        from_attributes = True


class AdminTeacherReport(BaseModel):
    teacher_id: int
    emis_id: str
    name: str
    district: str
    subject: Optional[str]
    school_name: Optional[str]
    total_posts: int
    total_views: int
    total_likes: int
    total_downloads: int
    total_comments: int
    engagement_score: float


class AdminMetricsResponse(BaseModel):
    total_teachers: int
    total_students: int
    total_posts: int
    total_views: int
    total_likes: int
    total_downloads: int
    total_comments: int


class DeletePostRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=1000)

    @validator('reason')
    def sanitize_reason(cls, v):
        return v.strip()


class DeletionLogResponse(BaseModel):
    id: int
    post_id: int
    post_title: str
    deleted_by_emis: str
    deleted_by_name: str
    deletion_reason: str
    deleted_at: datetime

    class Config:
        from_attributes = True
