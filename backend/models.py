from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


class EventType(str, enum.Enum):
    view = "view"
    download = "download"


class Album(Base):
    __tablename__ = "albums"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    cover_photo_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    photos = relationship("Photo", back_populates="album")


class Photo(Base):
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True, index=True)
    album_id = Column(Integer, ForeignKey("albums.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    r2_key_thumb = Column(String(500), nullable=False)
    r2_key_web = Column(String(500), nullable=False)
    r2_key_original = Column(String(500), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    album = relationship("Album", back_populates="photos")
    events = relationship("Event", back_populates="photo")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    photo_id = Column(Integer, ForeignKey("photos.id"), nullable=False)
    type = Column(Enum(EventType), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user_agent = Column(String(500), nullable=True)

    photo = relationship("Photo", back_populates="events")