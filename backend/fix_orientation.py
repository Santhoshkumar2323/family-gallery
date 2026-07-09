from pathlib import Path
from PIL import Image, ImageOps
from io import BytesIO
from tqdm import tqdm

from database import SessionLocal
from models import Photo, Album
from storage import s3_client, R2_BUCKET_NAME

RAW_PHOTOS_DIR = Path(__file__).resolve().parent.parent / "raw_photos"
THUMB_SIZE = (300, 300)
WEB_SIZE = (1920, 1920)

db = SessionLocal()


def resize_image(img: Image.Image, max_size: tuple) -> BytesIO:
    img = ImageOps.exif_transpose(img)  # <-- this is the fix
    img_copy = img.copy()
    img_copy.thumbnail(max_size, Image.LANCZOS)
    buffer = BytesIO()
    img_copy.convert("RGB").save(buffer, format="JPEG", quality=85)
    buffer.seek(0)
    return buffer


def upload_bytes(buffer: BytesIO, r2_key: str):
    s3_client.upload_fileobj(buffer, R2_BUCKET_NAME, r2_key)


def main():
    photos = db.query(Photo).all()
    print(f"Fixing orientation for {len(photos)} photos...")

    for photo in tqdm(photos):
        album = db.query(Album).filter(Album.id == photo.album_id).first()
        local_path = RAW_PHOTOS_DIR / album.name / photo.filename

        if not local_path.exists():
            print(f"\nMissing local file: {local_path}")
            continue

        img = Image.open(local_path)

        web_buf = resize_image(img, WEB_SIZE)
        upload_bytes(web_buf, photo.r2_key_web)

        thumb_buf = resize_image(img, THUMB_SIZE)
        upload_bytes(thumb_buf, photo.r2_key_thumb)

    print("Done fixing orientation.")


if __name__ == "__main__":
    main()