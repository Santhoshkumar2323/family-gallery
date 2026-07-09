from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from database import get_db
from models import Album, Photo, Event, EventType
from schemas import PinRequest, AlbumOut, PhotoOut, PhotoDetailOut, EventLog
from auth import check_pin, create_session_token, verify_session_token
from storage import get_signed_url

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

COOKIE_NAME = "family_gallery_session"


def require_auth(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    if not token or not verify_session_token(token):
        raise HTTPException(status_code=401, detail="Not authorized")
    return True


@app.post("/api/pin-check")
def pin_check(payload: PinRequest, response: Response):
    if not check_pin(payload.pin):
        raise HTTPException(status_code=401, detail="Incorrect PIN")
    token = create_session_token()
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )
    return {"success": True}


@app.get("/api/albums", response_model=list[AlbumOut])
def list_albums(request: Request, db: Session = Depends(get_db), _=Depends(require_auth)):
    albums = db.query(Album).all()
    result = []
    for album in albums:
        count = db.query(Photo).filter(Photo.album_id == album.id).count()
        result.append({"id": album.id, "name": album.name, "photo_count": count})
    return result


@app.get("/api/albums/{album_id}/photos", response_model=list[PhotoOut])
def list_photos(album_id: int, request: Request, db: Session = Depends(get_db), _=Depends(require_auth)):
    photos = db.query(Photo).filter(Photo.album_id == album_id).all()
    result = []
    for p in photos:
        result.append({
            "id": p.id,
            "filename": p.filename,
            "thumb_url": get_signed_url(p.r2_key_thumb, expiry=3600),
        })
    return result


@app.get("/api/photos/{photo_id}", response_model=PhotoDetailOut)
def get_photo_detail(photo_id: int, request: Request, db: Session = Depends(get_db), _=Depends(require_auth)):
    photo = db.query(Photo).filter(Photo.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    event = Event(photo_id=photo.id, type=EventType.view, user_agent=request.headers.get("user-agent"))
    db.add(event)
    db.commit()

    return {
        "id": photo.id,
        "filename": photo.filename,
        "web_url": get_signed_url(photo.r2_key_web, expiry=600),
        "download_url": get_signed_url(photo.r2_key_original, expiry=600),
    }


@app.post("/api/events/log")
def log_event(payload: EventLog, request: Request, db: Session = Depends(get_db), _=Depends(require_auth)):
    photo = db.query(Photo).filter(Photo.id == payload.photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    event_type = EventType.download if payload.type == "download" else EventType.view
    event = Event(photo_id=photo.id, type=event_type, user_agent=request.headers.get("user-agent"))
    db.add(event)
    db.commit()
    return {"success": True}


@app.get("/api/dashboard")
def dashboard_stats(request: Request, db: Session = Depends(get_db), _=Depends(require_auth)):
    total_views = db.query(Event).filter(Event.type == EventType.view).count()
    total_downloads = db.query(Event).filter(Event.type == EventType.download).count()

    top_photo_row = (
        db.query(Event.photo_id, func.count(Event.id).label("cnt"))
        .filter(Event.type == EventType.download)
        .group_by(Event.photo_id)
        .order_by(func.count(Event.id).desc())
        .first()
    )
    most_downloaded_photo = None
    if top_photo_row:
        photo = db.query(Photo).filter(Photo.id == top_photo_row.photo_id).first()
        if photo:
            most_downloaded_photo = {
                "id": photo.id,
                "filename": photo.filename,
                "count": top_photo_row.cnt,
                "thumb_url": get_signed_url(photo.r2_key_thumb, expiry=3600),
            }

    top_album_row = (
        db.query(Photo.album_id, func.count(Event.id).label("cnt"))
        .join(Event, Event.photo_id == Photo.id)
        .group_by(Photo.album_id)
        .order_by(func.count(Event.id).desc())
        .first()
    )
    most_popular_album = None
    if top_album_row:
        album = db.query(Album).filter(Album.id == top_album_row.album_id).first()
        if album:
            most_popular_album = {"name": album.name, "count": top_album_row.cnt}

    since = datetime.utcnow() - timedelta(days=14)
    timeline_rows = (
        db.query(func.date(Event.created_at).label("day"), func.count(Event.id).label("cnt"))
        .filter(Event.created_at >= since)
        .group_by(func.date(Event.created_at))
        .order_by(func.date(Event.created_at))
        .all()
    )
    timeline = [{"date": str(row.day), "count": row.cnt} for row in timeline_rows]

    recent_rows = (
        db.query(Event, Photo)
        .join(Photo, Event.photo_id == Photo.id)
        .order_by(Event.created_at.desc())
        .limit(15)
        .all()
    )
    recent_activity = [
        {
            "filename": photo.filename,
            "type": event.type.value,
            "created_at": event.created_at.isoformat(),
        }
        for event, photo in recent_rows
    ]

    return {
        "total_views": total_views,
        "total_downloads": total_downloads,
        "most_downloaded_photo": most_downloaded_photo,
        "most_popular_album": most_popular_album,
        "timeline": timeline,
        "recent_activity": recent_activity,
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}