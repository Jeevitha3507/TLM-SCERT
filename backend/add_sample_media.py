"""
Add sample media files (video, audio, image) to uploads/ and create
corresponding posts in the database linked to teacher TN000001.
Run from backend/: python add_sample_media.py
"""
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from database import SessionLocal, engine, Base
from models import Teacher, Post, Metric

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")

SAMPLES = [
    {
        "url": "https://samplelib.com/lib/preview/mp4/sample-5s.mp4",
        "filename": "sample_video.mp4",
        "file_type": "video",
        "title": "Sample Video TLM - Motion Demonstration",
        "subject": "Science",
        "grade": 8,
        "tlm_method": "Short video demonstrating physical motion concepts for classroom use.",
    },
    {
        "url": "https://samplelib.com/lib/preview/mp3/sample-3s.mp3",
        "filename": "sample_audio.mp3",
        "file_type": "audio",
        "title": "Sample Audio TLM - Pronunciation Guide",
        "subject": "English",
        "grade": 6,
        "tlm_method": "Audio clip for correct English pronunciation practice.",
    },
    {
        "url": "https://samplelib.com/lib/preview/jpeg/sample_640x426.jpg",
        "filename": "sample_image.jpg",
        "file_type": "image",
        "title": "Sample Image TLM - Visual Learning Aid",
        "subject": "Mathematics",
        "grade": 7,
        "tlm_method": "Visual chart used to explain mathematical concepts.",
    },
]


def _make_fallback_jpeg(dest: str):
    """Write a minimal valid 8x8 white JPEG when the download fails."""
    # Standard JFIF 1x1 white pixel JPEG bytes
    data = bytes([
        0xff,0xd8,0xff,0xe0,0x00,0x10,0x4a,0x46,0x49,0x46,0x00,0x01,0x01,0x00,
        0x00,0x01,0x00,0x01,0x00,0x00,0xff,0xdb,0x00,0x43,0x00,0x08,0x06,0x06,
        0x07,0x06,0x05,0x08,0x07,0x07,0x07,0x09,0x09,0x08,0x0a,0x0c,0x14,0x0d,
        0x0c,0x0b,0x0b,0x0c,0x19,0x12,0x13,0x0f,0x14,0x1d,0x1a,0x1f,0x1e,0x1d,
        0x1a,0x1c,0x1c,0x20,0x24,0x2e,0x27,0x20,0x22,0x2c,0x23,0x1c,0x1c,0x28,
        0x37,0x29,0x2c,0x30,0x31,0x34,0x34,0x34,0x1f,0x27,0x39,0x3d,0x38,0x32,
        0x3c,0x2e,0x33,0x34,0x32,0xff,0xc0,0x00,0x0b,0x08,0x00,0x01,0x00,0x01,
        0x01,0x01,0x11,0x00,0xff,0xc4,0x00,0x1f,0x00,0x00,0x01,0x05,0x01,0x01,
        0x01,0x01,0x01,0x01,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x01,0x02,
        0x03,0x04,0x05,0x06,0x07,0x08,0x09,0x0a,0x0b,0xff,0xc4,0x00,0xb5,0x10,
        0x00,0x02,0x01,0x03,0x03,0x02,0x04,0x03,0x05,0x05,0x04,0x04,0x00,0x00,
        0x01,0x7d,0x01,0x02,0x03,0x00,0x04,0x11,0x05,0x12,0x21,0x31,0x41,0x06,
        0x13,0x51,0x61,0x07,0x22,0x71,0x14,0x32,0x81,0x91,0xa1,0x08,0x23,0x42,
        0xb1,0xc1,0x15,0x52,0xd1,0xf0,0x24,0x33,0x62,0x72,0x82,0x09,0x0a,0x16,
        0x17,0x18,0x19,0x1a,0x25,0x26,0x27,0x28,0x29,0x2a,0x34,0x35,0x36,0x37,
        0x38,0x39,0x3a,0x43,0x44,0x45,0x46,0x47,0x48,0x49,0x4a,0x53,0x54,0x55,
        0x56,0x57,0x58,0x59,0x5a,0x63,0x64,0x65,0x66,0x67,0x68,0x69,0x6a,0x73,
        0x74,0x75,0x76,0x77,0x78,0x79,0x7a,0x83,0x84,0x85,0x86,0x87,0x88,0x89,
        0x8a,0x93,0x94,0x95,0x96,0x97,0x98,0x99,0x9a,0xa2,0xa3,0xa4,0xa5,0xa6,
        0xa7,0xa8,0xa9,0xaa,0xb2,0xb3,0xb4,0xb5,0xb6,0xb7,0xb8,0xb9,0xba,0xc2,
        0xc3,0xc4,0xc5,0xc6,0xc7,0xc8,0xc9,0xca,0xd2,0xd3,0xd4,0xd5,0xd6,0xd7,
        0xd8,0xd9,0xda,0xe1,0xe2,0xe3,0xe4,0xe5,0xe6,0xe7,0xe8,0xe9,0xea,0xf1,
        0xf2,0xf3,0xf4,0xf5,0xf6,0xf7,0xf8,0xf9,0xfa,0xff,0xda,0x00,0x08,0x01,
        0x01,0x00,0x00,0x3f,0x00,0xfb,0xd5,0xff,0xd9,
    ])
    with open(dest, "wb") as f:
        f.write(data)
    print(f"  Generated fallback JPEG: {dest} ({len(data):,} bytes)")


def download_file(url: str, dest: str):
    print(f"  Downloading {url} ...")
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://samplelib.com/",
            "Accept": "*/*",
        })
        with urllib.request.urlopen(req, timeout=30) as resp, open(dest, "wb") as f:
            f.write(resp.read())
        size = os.path.getsize(dest)
        print(f"  Saved {dest} ({size:,} bytes)")
    except Exception as e:
        print(f"  Download failed ({e}). Generating local fallback test file...")
        ext = os.path.splitext(dest)[1].lower()
        if ext in (".jpg", ".jpeg"):
            _make_fallback_jpeg(dest)
        else:
            raise


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    Base.metadata.create_all(bind=engine)

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    print(f"Uploads directory: {os.path.abspath(UPLOAD_DIR)}")

    print("\nDownloading sample files...")
    for sample in SAMPLES:
        dest = os.path.join(UPLOAD_DIR, sample["filename"])
        if os.path.exists(dest):
            print(f"  {dest} already exists, skipping download.")
        else:
            download_file(sample["url"], dest)

    print("\nCreating database posts...")
    db = SessionLocal()
    try:
        teacher = db.query(Teacher).filter(Teacher.emis_id == "TN000001").first()
        if not teacher:
            print("ERROR: Teacher TN000001 not found. Run seed.py first.")
            return

        print(f"  Using teacher: {teacher.name} (EMIS: {teacher.emis_id}, ID: {teacher.id})")

        for sample in SAMPLES:
            file_url = f"/uploads/{sample['filename']}"

            existing = db.query(Post).filter(Post.file_url == file_url).first()
            if existing:
                print(f"  Post already exists for {sample['filename']} (ID={existing.id}), skipping.")
                continue

            post = Post(
                teacher_id=teacher.id,
                title=sample["title"],
                subject=sample["subject"],
                grade=sample["grade"],
                tlm_method=sample["tlm_method"],
                file_url=file_url,
                file_type=sample["file_type"],
                original_filename=sample["filename"],
            )
            db.add(post)
            db.flush()

            metric = Metric(post_id=post.id)
            db.add(metric)

            print(f"  Created post ID={post.id}: [{sample['file_type']}] {sample['title']}")

        db.commit()
        print("\nDone! Sample posts created successfully.")
        print("\nFiles accessible at (when server is running):")
        for sample in SAMPLES:
            print(f"  http://localhost:8000/uploads/{sample['filename']}")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
