from pydantic import BaseModel
from datetime import datetime


class PinRequest(BaseModel):
    pin: str


class AlbumOut(BaseModel):
    id: int
    name: str
    photo_count: int

    class Config:
        from_attributes = True


class PhotoOut(BaseModel):
    id: int
    filename: str
    thumb_url: str

    class Config:
        from_attributes = True


class PhotoDetailOut(BaseModel):
    id: int
    filename: str
    web_url: str
    download_url: str

    class Config:
        from_attributes = True


class EventLog(BaseModel):
    photo_id: int
    type: str  # "view" or "download"


class DashboardStats(BaseModel):
    total_views: int
    total_downloads: int
    most_downloaded_photo: dict | None
    most_popular_album: dict | None
    timeline: list
    recent_activity: list