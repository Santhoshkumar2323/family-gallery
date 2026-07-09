import os
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
FAMILY_PIN = os.getenv("FAMILY_PIN")

serializer = URLSafeTimedSerializer(SECRET_KEY)

SESSION_MAX_AGE = 60 * 60 * 24 * 7  # 7 days


def check_pin(pin: str) -> bool:
    return pin == FAMILY_PIN


def create_session_token() -> str:
    return serializer.dumps({"authorized": True})


def verify_session_token(token: str) -> bool:
    try:
        data = serializer.loads(token, max_age=SESSION_MAX_AGE)
        return data.get("authorized", False)
    except (BadSignature, SignatureExpired):
        return False