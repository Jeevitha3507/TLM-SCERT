"""
EMIS simulation router.

Seed: 200 students × 5 subjects × 3 exams = 3 000 records
Classes: Grade 6-10, Sections A-D, 10 students per class
"""
import random
from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db
import models
from auth import get_current_teacher, get_current_admin

router = APIRouter(prefix="/emis", tags=["emis"])

# ─────────────────── seed constants ───────────────────
_FIRST_NAMES = [
    "Arjun", "Priya", "Karthik", "Divya", "Rajan", "Meena", "Siva", "Kavitha",
    "Ramesh", "Lakshmi", "Suresh", "Geetha", "Muthu", "Vimala", "Senthil", "Rani",
    "Ganesh", "Sumathi", "Bala", "Parvathi", "Mani", "Sangeetha", "Kumar", "Nithya",
    "Vijay", "Malathi", "Ravi", "Anitha", "Selvan", "Radha", "Devi", "Murugan",
    "Tamilarasi", "Selvakumar", "Anand", "Bharathi", "Chandran", "Eswari", "Gopi", "Hema",
]
_LAST_NAMES = [
    "Kumar", "Raj", "Rajan", "Murthy", "Pillai", "Naidu", "Murugan", "Krishnan",
    "Sundaram", "Perumal", "Gopal", "Mani", "Arumugam", "Selvam", "Durai",
    "Pandian", "Natarajan", "Srinivasan", "Venkat", "Balan",
]
_TN_DISTRICTS = [
    "Ariyalur", "Chengalpattu", "Chennai", "Coimbatore", "Cuddalore",
    "Dharmapuri", "Dindigul", "Erode", "Kallakurichi", "Kancheepuram",
    "Karur", "Krishnagiri", "Madurai", "Mayiladuthurai", "Nagapattinam",
    "Namakkal", "Nilgiris", "Perambalur", "Pudukkottai", "Ramanathapuram",
    "Ranipet", "Salem", "Sivaganga", "Tenkasi", "Thanjavur", "Theni",
    "Thoothukudi", "Tiruchirappalli", "Tirunelveli", "Tirupathur",
    "Tiruppur", "Tiruvallur", "Tiruvannamalai", "Tiruvarur", "Vellore",
    "Villupuram", "Virudhunagar", "Kanyakumari",
]
# (base_lo, base_hi, improvement_lo, improvement_hi)
_SUBJECT_PARAMS = {
    "Mathematics":    (42, 68, 3, 12),
    "Science":        (45, 70, 3, 11),
    "Tamil":          (52, 78, 2, 10),
    "English":        (38, 65, 3, 13),
    "Social Science": (48, 74, 3, 11),
}
_EXAM_SCHEDULE = [
    ("Quarterly",   datetime(2024, 8, 15)),
    ("Half Yearly", datetime(2024, 12, 10)),
    ("Annual",      datetime(2025, 3, 20)),
]
_CORE_SUBJECTS = list(_SUBJECT_PARAMS.keys())


# ─────────────────── migration + seeding ───────────────────
def _migrate_columns(db: Session) -> None:
    for col, col_type in [
        ("section",     "VARCHAR(5)"),
        ("district",    "VARCHAR(100)"),
        ("school_name", "VARCHAR(200)"),
    ]:
        try:
            db.execute(text(f"ALTER TABLE emis_exam_marks ADD COLUMN {col} {col_type}"))
            db.commit()
        except Exception:
            pass  # column already exists


def seed_emis_marks(db: Session) -> None:
    _migrate_columns(db)

    count = db.query(models.EmisExamMark).count()
    if count >= 2_000:
        return  # already seeded with new format

    db.query(models.EmisExamMark).delete()
    db.commit()

    rng = random.Random(42)
    records: list[models.EmisExamMark] = []

    for i in range(1, 201):
        student_emis = f"ST{i:07d}"
        name = f"{rng.choice(_FIRST_NAMES)} {rng.choice(_LAST_NAMES)}"

        class_idx = (i - 1) // 10
        grade = 6 + (class_idx // 4)
        section = chr(65 + (class_idx % 4))
        district = _TN_DISTRICTS[(i - 1) % len(_TN_DISTRICTS)]
        school_name = f"GHSS {district}"

        study_factor = rng.uniform(0.6, 1.5)

        for subj, (base_lo, base_hi, imp_lo, imp_hi) in _SUBJECT_PARAMS.items():
            q_mark = rng.randint(base_lo, base_hi)
            hy_gain = max(1, int(rng.randint(imp_lo, imp_hi) * study_factor))
            an_gain = max(1, int(rng.randint(imp_lo, imp_hi) * study_factor))
            hy_mark = min(100, q_mark + hy_gain)
            an_mark = min(100, hy_mark + an_gain)

            for exam_type, exam_date, mark in [
                ("Quarterly",   _EXAM_SCHEDULE[0][1], q_mark),
                ("Half Yearly", _EXAM_SCHEDULE[1][1], hy_mark),
                ("Annual",      _EXAM_SCHEDULE[2][1], an_mark),
            ]:
                records.append(models.EmisExamMark(
                    student_emis=student_emis,
                    student_name=name,
                    grade=grade,
                    section=section,
                    district=district,
                    school_name=school_name,
                    subject=subj,
                    exam_type=exam_type,
                    exam_date=exam_date,
                    marks_obtained=mark,
                    total_marks=100,
                    academic_year="2024-2025",
                ))

    db.add_all(records)
    db.commit()
    print(f"Seeded {len(records)} EMIS exam marks "
          f"(200 students × 5 subjects × 3 exams)")


# ─────────────────── helpers ───────────────────
def _improvement_pct(annual: int, quarterly: int) -> float:
    if quarterly == 0:
        return 0.0
    return round(((annual - quarterly) / quarterly) * 100, 1)


def _trend(annual: int, quarterly: int) -> str:
    if annual > quarterly:
        return "up"
    if annual < quarterly:
        return "down"
    return "same"


def _build_student_row(emis: str, info: dict, exams: dict) -> dict:
    q  = exams.get("Quarterly", 0)
    hy = exams.get("Half Yearly", 0)
    an = exams.get("Annual", 0)
    return {
        **info,
        "quarterly":       q,
        "half_yearly":     hy,
        "annual":          an,
        "improvement_pct": _improvement_pct(an, q),
        "trend":           _trend(an, q),
    }


# ─────────────────── teacher endpoints ───────────────────
@router.get("/meta")
def get_emis_meta(
    current_user=Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """Available filter values for the class comparison page."""
    rows = db.query(
        models.EmisExamMark.grade,
        models.EmisExamMark.section,
        models.EmisExamMark.subject,
        models.EmisExamMark.academic_year,
    ).distinct().all()

    return {
        "grades":         sorted({r.grade for r in rows}),
        "sections":       sorted({r.section for r in rows if r.section}),
        "subjects":       sorted({r.subject for r in rows}),
        "academic_years": sorted({r.academic_year for r in rows}, reverse=True),
    }


@router.get("/class")
def get_class_comparison(
    grade:         int = Query(...),
    section:       str = Query(...),
    subject:       str = Query(...),
    academic_year: str = Query("2024-2025"),
    current_user=Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    marks = (
        db.query(models.EmisExamMark)
        .filter(
            models.EmisExamMark.grade == grade,
            models.EmisExamMark.section == section,
            models.EmisExamMark.subject == subject,
            models.EmisExamMark.academic_year == academic_year,
        )
        .order_by(models.EmisExamMark.student_emis, models.EmisExamMark.exam_date)
        .all()
    )

    if not marks:
        return {
            "grade": grade, "section": section,
            "subject": subject, "academic_year": academic_year,
            "total_students": 0, "students": [],
            "class_average": None, "best_improved": None,
        }

    student_exams: dict = defaultdict(dict)
    student_info:  dict = {}
    for m in marks:
        emis = m.student_emis
        student_info[emis] = {
            "student_emis": emis,
            "student_name": m.student_name,
            "grade":        m.grade,
            "section":      m.section,
            "district":     m.district,
        }
        student_exams[emis][m.exam_type] = m.marks_obtained

    students = sorted(
        [_build_student_row(e, student_info[e], student_exams[e]) for e in student_exams],
        key=lambda s: s["student_name"],
    )

    n = len(students)
    avg_q  = round(sum(s["quarterly"]   for s in students) / n, 1)
    avg_hy = round(sum(s["half_yearly"] for s in students) / n, 1)
    avg_an = round(sum(s["annual"]      for s in students) / n, 1)
    class_average = {
        "quarterly":       avg_q,
        "half_yearly":     avg_hy,
        "annual":          avg_an,
        "improvement_pct": _improvement_pct(avg_an, avg_q),
    }

    best_improved = max(students, key=lambda s: s["improvement_pct"]) if students else None

    return {
        "grade":          grade,
        "section":        section,
        "subject":        subject,
        "academic_year":  academic_year,
        "total_students": n,
        "students":       students,
        "class_average":  class_average,
        "best_improved":  best_improved,
    }


@router.get("/student/{emis}/marks")
def get_student_emis_marks(
    emis: str,
    current_user=Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    marks = (
        db.query(models.EmisExamMark)
        .filter(models.EmisExamMark.student_emis == emis)
        .order_by(models.EmisExamMark.exam_date)
        .all()
    )
    return {
        "student_emis": emis,
        "student_name": marks[0].student_name if marks else None,
        "marks": [
            {
                "id":             m.id,
                "subject":        m.subject,
                "grade":          m.grade,
                "section":        m.section,
                "exam_type":      m.exam_type,
                "exam_date":      m.exam_date.strftime("%Y-%m-%d"),
                "marks_obtained": m.marks_obtained,
                "total_marks":    m.total_marks,
                "academic_year":  m.academic_year,
            }
            for m in marks
        ],
    }


@router.get("/student/{emis}/subjects")
def get_student_all_subjects(
    emis: str,
    academic_year: str = Query("2024-2025"),
    current_user=Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    marks = (
        db.query(models.EmisExamMark)
        .filter(
            models.EmisExamMark.student_emis == emis,
            models.EmisExamMark.academic_year == academic_year,
        )
        .order_by(models.EmisExamMark.subject, models.EmisExamMark.exam_date)
        .all()
    )
    if not marks:
        return {"student_emis": emis, "student_name": None, "subjects": []}

    first = marks[0]
    subj_exams: dict = defaultdict(dict)
    for m in marks:
        subj_exams[m.subject][m.exam_type] = m.marks_obtained

    subjects = []
    for subj, exams in subj_exams.items():
        q  = exams.get("Quarterly", 0)
        hy = exams.get("Half Yearly", 0)
        an = exams.get("Annual", 0)
        subjects.append({
            "subject":        subj,
            "quarterly":      q,
            "half_yearly":    hy,
            "annual":         an,
            "improvement_pct": _improvement_pct(an, q),
            "trend":          _trend(an, q),
        })

    return {
        "student_emis": emis,
        "student_name": first.student_name,
        "grade":        first.grade,
        "section":      first.section,
        "district":     first.district,
        "school_name":  first.school_name,
        "academic_year": academic_year,
        "subjects":     subjects,
    }


# ─────────────────── admin endpoints ───────────────────
def _aggregate(marks, key_fn) -> list[dict]:
    groups: dict = defaultdict(lambda: defaultdict(list))
    for m in marks:
        groups[key_fn(m)][m.exam_type].append(m.marks_obtained)

    result = []
    for group_key, exams in groups.items():
        ql  = exams.get("Quarterly", [0])
        hyl = exams.get("Half Yearly", [0])
        anl = exams.get("Annual", [0])
        avg_q  = round(sum(ql)  / len(ql), 1)
        avg_hy = round(sum(hyl) / len(hyl), 1)
        avg_an = round(sum(anl) / len(anl), 1)
        result.append({
            "name":             group_key,
            "quarterly_avg":   avg_q,
            "half_yearly_avg": avg_hy,
            "annual_avg":      avg_an,
            "improvement_pct": _improvement_pct(avg_an, avg_q),
            "student_count":   len(set()),  # placeholder
        })
    result.sort(key=lambda x: -x["improvement_pct"])
    return result


@router.get("/admin/by-subject")
def admin_by_subject(
    academic_year: str = Query("2024-2025"),
    admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    marks = db.query(models.EmisExamMark).filter(
        models.EmisExamMark.academic_year == academic_year
    ).all()

    groups: dict = defaultdict(lambda: defaultdict(list))
    for m in marks:
        groups[m.subject][m.exam_type].append(m.marks_obtained)

    result = []
    for subj, exams in groups.items():
        ql  = exams.get("Quarterly", [0])
        hyl = exams.get("Half Yearly", [0])
        anl = exams.get("Annual", [0])
        avg_q  = round(sum(ql)  / len(ql), 1)
        avg_hy = round(sum(hyl) / len(hyl), 1)
        avg_an = round(sum(anl) / len(anl), 1)
        result.append({
            "subject":         subj,
            "quarterly_avg":   avg_q,
            "half_yearly_avg": avg_hy,
            "annual_avg":      avg_an,
            "improvement_pct": _improvement_pct(avg_an, avg_q),
        })
    result.sort(key=lambda x: -x["improvement_pct"])
    return result


@router.get("/admin/by-district")
def admin_by_district(
    subject:       str | None = None,
    academic_year: str = Query("2024-2025"),
    admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    q = db.query(models.EmisExamMark).filter(
        models.EmisExamMark.academic_year == academic_year
    )
    if subject:
        q = q.filter(models.EmisExamMark.subject == subject)
    marks = q.all()

    groups: dict = defaultdict(lambda: defaultdict(list))
    student_sets: dict = defaultdict(set)
    for m in marks:
        dist = m.district or "Unknown"
        groups[dist][m.exam_type].append(m.marks_obtained)
        student_sets[dist].add(m.student_emis)

    result = []
    for dist, exams in groups.items():
        ql  = exams.get("Quarterly", [0])
        hyl = exams.get("Half Yearly", [0])
        anl = exams.get("Annual", [0])
        avg_q  = round(sum(ql)  / len(ql), 1)
        avg_hy = round(sum(hyl) / len(hyl), 1)
        avg_an = round(sum(anl) / len(anl), 1)
        result.append({
            "district":        dist,
            "quarterly_avg":   avg_q,
            "half_yearly_avg": avg_hy,
            "annual_avg":      avg_an,
            "improvement_pct": _improvement_pct(avg_an, avg_q),
            "student_count":   len(student_sets[dist]),
        })
    result.sort(key=lambda x: -x["improvement_pct"])
    return result


@router.get("/admin/by-grade")
def admin_by_grade(
    subject:       str | None = None,
    academic_year: str = Query("2024-2025"),
    admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    q = db.query(models.EmisExamMark).filter(
        models.EmisExamMark.academic_year == academic_year
    )
    if subject:
        q = q.filter(models.EmisExamMark.subject == subject)
    marks = q.all()

    groups: dict = defaultdict(lambda: defaultdict(list))
    for m in marks:
        groups[m.grade][m.exam_type].append(m.marks_obtained)

    result = []
    for grade, exams in sorted(groups.items()):
        ql  = exams.get("Quarterly", [0])
        hyl = exams.get("Half Yearly", [0])
        anl = exams.get("Annual", [0])
        avg_q  = round(sum(ql)  / len(ql), 1)
        avg_hy = round(sum(hyl) / len(hyl), 1)
        avg_an = round(sum(anl) / len(anl), 1)
        result.append({
            "grade":           grade,
            "quarterly_avg":   avg_q,
            "half_yearly_avg": avg_hy,
            "annual_avg":      avg_an,
            "improvement_pct": _improvement_pct(avg_an, avg_q),
        })
    return result
