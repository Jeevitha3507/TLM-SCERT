# TLM Connect
**Tamil Nadu School Education Department — Teaching Learning Material Platform**

A full-stack web application for sharing and discovering Teaching Learning Materials (TLM) across Tamil Nadu schools.

---

## Tech Stack
- **Frontend**: React 18 + Vite + Tailwind CSS
- **Backend**: Python FastAPI + WebSockets
- **Database**: PostgreSQL (port 1234)

---

## Prerequisites

| Tool | Version | Download |
|------|---------|----------|
| Python | 3.10+ | python.org |
| Node.js | 18+ | nodejs.org |
| PostgreSQL | 14+ | postgresql.org |

Make sure PostgreSQL is running on **port 1234** with:
- Username: `postgres`
- Password: `postgres123`
- Database: `tlmconnect` (create it first)

---

## Setup Steps

### 1. Create the Database

Open pgAdmin or psql and run:
```sql
CREATE DATABASE tlmconnect;
```

### 2. Backend Setup

```powershell
cd C:\Users\HP\tlmconnect\backend

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Seed sample data (100 teachers, 200 students, sample posts)
python seed.py

# Start the API server
uvicorn main:app --reload --port 8000
```

Backend will be available at: http://localhost:8000  
API docs (Swagger UI): http://localhost:8000/docs

### 3. Frontend Setup

Open a **new terminal**:

```powershell
cd C:\Users\HP\tlmconnect\frontend

# Install Node dependencies
npm install

# Start the dev server
npm run dev
```

Frontend will be at: http://localhost:5173

---

## Login Credentials

| Role | EMIS ID / Number | Password |
|------|-----------------|----------|
| SCERT Admin | `SCERT001` | `scert@admin123` |
| Sample Teacher | `TN000001` to `TN000100` | `teacher@123` |
| Sample Student | `ST0000001` to `ST0000200` | *(no password)* |

---

## Features

### Feed Page (`/feed`)
- Browse all TLM posts from teachers across Tamil Nadu
- Filter by subject, grade, district
- Search by title
- Load more pagination

### Post Detail (`/post/:id`)
- Full post view with file preview (video/audio/image/document)
- Real-time WebSocket comments
- Like / Download / Share buttons
- View count, like count, download count

### Upload Page (`/upload`) — Teachers only
- Upload TLM with title, subject, grade, description
- Supports: video (max 100MB), audio/image/document (max 10MB)
- Drag-and-drop file upload with progress bar

### Admin Panel (`/admin`) — SCERT only
- Overview stats: total teachers, students, posts, views, likes, downloads
- Teacher rankings by engagement score
- Filter by district, subject, grade
- Export full report as CSV

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `schools` | School info with UDISE code |
| `teachers` | Teacher accounts (EMIS ID + bcrypt password) |
| `students` | Student records (EMIS number, read-only access) |
| `posts` | TLM content with file metadata |
| `comments` | Post comments (teachers + students) |
| `likes` | Like records per post per user |
| `downloads` | Download records per post per user |
| `views` | View records per post per user |
| `metrics` | Denormalized counts for fast reads |

---

## API Endpoints

### Auth
- `POST /api/auth/teacher/login` — Teacher / Admin login
- `POST /api/auth/student/view` — Student read-only access
- `GET /api/auth/me` — Current user info

### Posts
- `GET /api/posts` — List posts (filters: subject, grade, district, search)
- `POST /api/posts` — Upload new post (multipart/form-data)
- `GET /api/posts/{id}` — Get single post (records view)
- `POST /api/posts/{id}/like` — Toggle like
- `POST /api/posts/{id}/download` — Record download

### Comments
- `GET /api/posts/{id}/comments` — Get comments
- `POST /api/posts/{id}/comments` — Add comment (REST fallback)
- `WS /ws/comments/{id}` — Real-time WebSocket comments

### Admin
- `GET /api/admin/metrics` — Overall statistics
- `GET /api/admin/teachers` — Teacher rankings (filterable)
- `GET /api/admin/export` — Download CSV report

### Metadata
- `GET /api/meta/subjects` — List of subjects
- `GET /api/meta/districts` — List of 38 TN districts

---

## Security
- JWT tokens (7-day expiry, HS256)
- bcrypt password hashing
- SQL injection prevention via SQLAlchemy ORM
- File type + size validation on upload
- CORS restricted to frontend origin
- Students get read-only JWT (no upload/admin access)

---

## Engagement Score Formula
```
score = (views × 1) + (likes × 3) + (downloads × 2) + (comments × 2)
```

---

## Troubleshooting

**PostgreSQL connection error**: Verify PostgreSQL is on port 1234. Check `backend/.env` DATABASE_URL.

**`uvicorn` not found**: Activate the venv first: `.\venv\Scripts\activate`

**CORS errors**: Ensure frontend runs on port 5173 and backend on 8000.

**File uploads failing**: Check the `backend/uploads/` directory exists (created automatically).

**WebSocket not connecting**: The Vite proxy handles WS in dev. Make sure both servers are running.
