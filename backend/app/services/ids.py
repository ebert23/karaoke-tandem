"""Generación de IDs cortos y legibles, y utilidades de fecha."""
import uuid
from datetime import datetime


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
