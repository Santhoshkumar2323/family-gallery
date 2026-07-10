# Family Gallery

A private, PIN-gated photo gallery built for sharing full-resolution engagement photos with family. 

Built as a small full-stack system rather than relying on a public file-sharing link, with proper access control, an image processing pipeline and a dashboard.

Live app: https://family-gallery-nine.vercel.app

(PIN is shared privately with family, not listed here.)

# Features

Album-based photo browsing 

Full original-quality downloads (thumbnails/web sizes are for browsing only, never what gets downloaded)

PIN-based access — no individual accounts needed

Analytics dashboard: total views/downloads, most downloaded photo, most popular album, 14-day activity timeline, recent activity feed

# Tech Stack

Backend = FastAPI (Python), SQLAlchemy

Database = MySQL (Aiven, free tier)

Storage = Cloudflare R2 (S3-compatible object storage)

Frontend = Plain HTML/CSS/JavaScript

Image processing = Pillow

Backend hosting = Render (free tier)

Frontend hosting = Vercel (free tier)

Total hosting cost: $0/month.


# Architecture

Browser → Vercel (frontend) → Render (FastAPI backend) → Aiven MySQL (metadata) → Cloudflare R2 (photo files)

The frontend never talks to the database or storage directly. Every photo request goes through the backend, which checks the session token and generates a short-lived signed URL before the browser fetches the actual image from R2.


# Design Decisions

Signed URLs instead of a public bucket — the R2 bucket is private. Every image request is authorized individually and the resulting URL expires within minutes, so links can't be indefinitely shared or reused.

Three image sizes per photo — thumbnail (fast grid loading), web (fast full-screen viewing), and original (untouched, only ever served on explicit download). This keeps the gallery fast to browse without ever compressing what people actually download.

Token-based auth instead of cookies — the frontend and backend run on different domains (Vercel and Render), and browsers increasingly block third-party cookies by default. Sessions are instead stored as a signed token in localStorage and sent via an Authorization header, which works reliably across domains and browsers.

Folder-per-album upload convention — dropping photos into named subfolders before running the upload script automatically creates matching albums, with no manual tagging step.


# Local Development Setup

Requirements: Python 3.11+, Docker, Node not required (frontend has no build step).

1. Clone the repo

2. cd backend, create/activate a virtual environment, then:

pip install -r requirements.txt

3. Start a local MySQL instance:

docker-compose up -d

4. Create backend/.env with the following variables (values not included in this repo):

   DATABASE_URL=

   R2_ACCOUNT_ID=

   R2_ACCESS_KEY_ID=

   R2_SECRET_ACCESS_KEY=

   R2_BUCKET_NAME=

   R2_ENDPOINT_URL=

   SIGNED_URL_EXPIRY_SECONDS=600

   FAMILY_PIN=

   SECRET_KEY=

5. Create the database tables:

python -c "from database import Base, engine; import models; Base.metadata.create_all(bind=engine)"

6. Run the backend:

uvicorn main:app --reload

7. Open frontend/index.html with a local static server (e.g. VS Code's Live Server extension)


# Project Structure

family-gallery/
├── backend/
│   ├── main.py            # API routes
│   ├── database.py        # DB connection setup
│   ├── models.py          # Album, Photo, Event tables
│   ├── schemas.py         # Request/response validation
│   ├── auth.py             # PIN check + session token logic
│   ├── storage.py         # R2 upload + signed URL generation
│   ├── upload_script.py   # Batch photo upload + processing
│   ├── fix_orientation.py # EXIF orientation correction 
│   └── requirements.txt
├── frontend/
│   ├── index.html         # PIN entry
│   ├── gallery.html       # Album list + photo grid
│   ├── dashboard.html     # Analytics dashboard
│   ├── app.js
│   └── style.css
└── docker-compose.yml      # Local MySQL for development


# Notable Problems Solved while building


EXIF orientation metadata was lost during image resizing, causing sideways thumbnails — fixed by applying ImageOps.exif_transpose() before resize.

Cross-origin downloads were silently blocked by the browser — fixed by fetching images as blobs before triggering a same-origin download.

SSL certificate verification failed against Aiven's managed MySQL — resolved by configuring a custom SSL context for that connection.

Aiven's free tier drops idle database connections — resolved with SQLAlchemy's pool_recycle.

Cross-site cookies were silently rejected by browsers once frontend and backend were split across domains — resolved by switching to token-based auth via localStorage and an Authorization header.

Render's free tier spins down after 15 minutes of inactivity, causing slow first loads — mitigated with a scheduled keep-alive ping.

# Security Notes

R2 bucket is private; all access is through time-limited signed URLs

Session tokens are cryptographically signed and expire after 7 days

Secrets (.env, database credentials, API keys) are excluded from version control

CORS is restricted to known frontend origins only


# Author

Santhosh Kumar




