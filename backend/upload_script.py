import os
from pathlib import Path
from PIL import Image
from io import BytesIO
from tqdm import tqdm

from database import SessionLocal, engine, Base
from models import Album, Photo
from storage import s3_client, R2_BUCKET_NAME

# ---- CONFIG ----
RAW_PHOTOS_DIR = Path(__file__).resolve().parent.parent / "raw_photos"
THUMB_SIZE = (300, 300)
WEB_SIZE = (1920, 1920)

Base.metadata.create_all(bind=engine)
db = SessionLocal()


def resize_image(img: Image.Image, max_size: tuple) -> BytesIO:
    img_copy = img.copy()
    img_copy.thumbnail(max_size, Image.LANCZOS)
    buffer = BytesIO()
    img_copy.convert("RGB").save(buffer, format="JPEG", quality=85)
    buffer.seek(0)
    return buffer


def upload_bytes(buffer: BytesIO, r2_key: str):
    s3_client.upload_fileobj(buffer, R2_BUCKET_NAME, r2_key)


def get_or_create_album(name: str) -> Album:
    album = db.query(Album).filter(Album.name == name).first()
    if not album:
        album = Album(name=name)
        db.add(album)
        db.commit()
        db.refresh(album)
    return album


def main():
    if not RAW_PHOTOS_DIR.exists():
        print(f"ERROR: {RAW_PHOTOS_DIR} does not exist.")
        return

    album_folders = [f for f in RAW_PHOTOS_DIR.iterdir() if f.is_dir()]
    if not album_folders:
        print("No album folders found inside raw_photos/.")
        return

    total_uploaded = 0
    total_skipped = 0

    for folder in album_folders:
        album_name = folder.name
        photo_files = [f for f in folder.iterdir() if f.suffix.lower() in (".jpg", ".jpeg")]

        if not photo_files:
            print(f"Skipping '{album_name}' — no JPG files found.")
            continue

        album = get_or_create_album(album_name)
        print(f"\nAlbum: {album_name} ({len(photo_files)} photos)")

        for photo_path in tqdm(photo_files, desc=album_name):
            filename = photo_path.name

            existing = (
                db.query(Photo)
                .filter(Photo.album_id == album.id, Photo.filename == filename)
                .first()
            )
            if existing:
                total_skipped += 1
                continue

            try:
                img = Image.open(photo_path)

                safe_name = photo_path.stem.replace(" ", "_")
                r2_key_original = f"{album_name}/original/{safe_name}.jpg"
                r2_key_web = f"{album_name}/web/{safe_name}.jpg"
                r2_key_thumb = f"{album_name}/thumb/{safe_name}.jpg"

                # Original — upload as-is
                s3_client.upload_file(str(photo_path), R2_BUCKET_NAME, r2_key_original)

                # Web size
                web_buf = resize_image(img, WEB_SIZE)
                upload_bytes(web_buf, r2_key_web)

                # Thumbnail
                thumb_buf = resize_image(img, THUMB_SIZE)
                upload_bytes(thumb_buf, r2_key_thumb)

                photo = Photo(
                    album_id=album.id,
                    filename=filename,
                    r2_key_thumb=r2_key_thumb,
                    r2_key_web=r2_key_web,
                    r2_key_original=r2_key_original,
                )
                db.add(photo)
                db.commit()
                total_uploaded += 1

            except Exception as e:
                print(f"\nFailed on {filename}: {e}")
                db.rollback()

    print(f"\nDone. Uploaded: {total_uploaded}, Skipped (already existed): {total_skipped}")


if __name__ == "__main__":
    main()