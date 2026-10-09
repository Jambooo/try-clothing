import threading
import secrets
import hmac
import hashlib
import io
import os
import time
import uuid
from pathlib import Path
from PIL import Image, ImageOps, UnidentifiedImageError
from dotenv import load_dotenv
from sqlalchemy import JSON, Float, String, Boolean, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
DATA = ROOT / "data"
MEDIA = DATA / "media"
MEDIA.mkdir(parents=True, exist_ok=True)
engine = create_engine("sqlite:///" + str(DATA / "app.db"), connect_args={"check_same_thread": False})

task_lock = threading.RLock()

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    nickname: Mapped[str] = mapped_column(String, default="衣见用户")
    avatar_id: Mapped[str | None] = mapped_column(String, nullable=True)
    unionid: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    profile: Mapped[dict] = mapped_column(JSON, default=dict)
    consent_version: Mapped[str] = mapped_column(String, default="")
    disabled: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created: Mapped[float] = mapped_column(Float, default=time.time)

class Identity(Base):
    __tablename__ = "identities"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    provider_key: Mapped[str] = mapped_column(String, unique=True)

class LoginSession(Base):
    __tablename__ = "login_sessions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    token_hash: Mapped[str] = mapped_column(String, unique=True)
    refresh_hash: Mapped[str] = mapped_column(String, unique=True)
    expires: Mapped[float] = mapped_column(Float)
    refresh_expires: Mapped[float] = mapped_column(Float)
    created: Mapped[float] = mapped_column(Float, default=time.time)

class OAuthState(Base):
    __tablename__ = "oauth_states"
    state_hash: Mapped[str] = mapped_column(String, primary_key=True)
    channel: Mapped[str] = mapped_column(String)
    challenge: Mapped[str] = mapped_column(String)
    expires: Mapped[float] = mapped_column(Float)

class UsageEvent(Base):
    __tablename__ = "usage_events"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    owner_id: Mapped[str] = mapped_column(String, index=True)
    kind: Mapped[str] = mapped_column(String)
    created: Mapped[float] = mapped_column(Float, default=time.time, index=True)

class Feedback(Base):
    status: Mapped[str] = mapped_column(String, default="new")
    reply: Mapped[str] = mapped_column(String, default="")
    replied_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    __tablename__ = "feedback"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    content: Mapped[str] = mapped_column(String)
    created: Mapped[float] = mapped_column(Float, default=time.time)

class Asset(Base):
    favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    __tablename__ = "assets"
    owner_id: Mapped[str] = mapped_column(String, index=True, default="local-developer")
    id: Mapped[str] = mapped_column(String, primary_key=True)
    kind: Mapped[str] = mapped_column(String)
    source: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    profile: Mapped[dict] = mapped_column(JSON, default=dict)
    created: Mapped[float] = mapped_column(Float, default=time.time)

class Task(Base):
    __tablename__ = "tasks"
    owner_id: Mapped[str] = mapped_column(String, index=True, default="local-developer")
    id: Mapped[str] = mapped_column(String, primary_key=True)
    kind: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="queued")
    snapshot: Mapped[dict] = mapped_column(JSON)
    provider_id: Mapped[str | None] = mapped_column(String, nullable=True)
    result_id: Mapped[str | None] = mapped_column(String, nullable=True)
    error: Mapped[str | None] = mapped_column(String, nullable=True)
    created: Mapped[float] = mapped_column(Float, default=time.time)
    output_url: Mapped[str | None] = mapped_column(String, nullable=True)

def media_link(asset_id):
    path = "/media/" + asset_id + ".jpg"
    if os.getenv("IMAGE_UPLOAD_MODE", "temporary") == "public":
        return path
    expires = int(time.time()) + 24 * 3600
    secret = os.getenv("MEDIA_SIGNING_KEY") or signing_secret()
    signature = hmac.new(secret.encode(), f"{asset_id}:{expires}".encode(), hashlib.sha256).hexdigest()
    return f"{path}?expires={expires}&signature={signature}"

def valid_media_signature(asset_id, expires, signature):
    if expires < time.time() or expires > time.time() + 25 * 3600:
        return False
    secret = os.getenv("MEDIA_SIGNING_KEY") or signing_secret()
    expected = hmac.new(secret.encode(), f"{asset_id}:{expires}".encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

def asset_data(a):
    return dict(id=a.id, kind=a.kind, source=a.source, name=a.name, profile=a.profile,
                url=media_link(a.id), created=a.created, favorite=a.favorite)

def task_data(t):
    with Session(engine) as s:
        a = s.get(Asset, t.result_id) if t.result_id else None
        return dict(id=t.id, kind=t.kind, status=t.status, snapshot=t.snapshot,
                    error=t.error, created=t.created, result=asset_data(a) if a else None)

def update(key, **values):
    with Session(engine) as s:
        t = s.get(Task, key)
        for k, v in values.items():
            setattr(t, k, v)
        s.commit()

def save_image(raw, kind, source, name, profile=None, owner_id="local-developer"):
    try:
        with Image.open(io.BytesIO(raw)) as original:
            if original.width * original.height > 24_000_000:
                raise ValueError("图片像素过大，最多 2400 万像素")
            image = ImageOps.exif_transpose(original).convert("RGB")
            minimum=32 if kind=="avatar" else 150
            if min(image.size) < minimum:
                raise ValueError(f"图片宽高至少 {minimum} 像素")
            image.thumbnail((1440, 1440))
            key = uuid.uuid4().hex
            image.save(MEDIA / (key + ".jpg"), "JPEG", quality=94)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as e:
        raise ValueError("无法读取图片，请使用 JPG、PNG 或 WebP") from e
    try:
        with task_lock, Session(engine) as s:
            from sqlalchemy import select, func
            account=s.get(User,owner_id)
            if not account or account.deleted or account.disabled:
                raise ValueError("账号已停用，请重新登录")
            count=s.scalar(select(func.count()).select_from(Asset).where(Asset.owner_id==owner_id))
            total=s.scalar(select(func.count()).select_from(Asset))
            reserved_own=reserved_total=0
            if source=="upload":
                reserved_own=s.scalar(select(func.count()).select_from(Task).where(Task.owner_id==owner_id,Task.status.in_(["queued","running","saving"])))
                reserved_total=s.scalar(select(func.count()).select_from(Task).where(Task.status.in_(["queued","running","saving"])))
            if count+reserved_own>=int(os.getenv("MAX_ASSETS_PER_USER","1000")) or total+reserved_total>=int(os.getenv("MAX_ASSETS_TOTAL","10000")):
                raise ValueError("素材存储额度已满，请先删除不需要的图片")
            a = Asset(id=key, owner_id=owner_id, kind=kind, source=source, name=name[:120], profile=profile or {})
            s.add(a)
            s.commit()
            return asset_data(a)
    except Exception:
        (MEDIA / (key + ".jpg")).unlink(missing_ok=True)
        raise



def signing_secret():
    configured = os.getenv("MEDIA_SIGNING_KEY")
    if configured:
        return configured
    # A persistent local secret; excluded along with all data from source control.
    path = DATA / ".media-secret"
    if not path.exists():
        try:
            with path.open("x", encoding="utf-8") as handle:
                handle.write(secrets.token_hex(32))
        except FileExistsError:
            pass
    return path.read_text(encoding="utf-8").strip()


def cleanup_accounts():
    from sqlalchemy import select, delete
    with task_lock, Session(engine) as s:
        for user in s.scalars(select(User).where(User.deleted == True)):
            try:
                for asset in s.scalars(select(Asset).where(Asset.owner_id == user.id)):
                    (MEDIA / (asset.id + ".jpg")).unlink(missing_ok=True)
                for model, column in [(Asset,Asset.owner_id),(Task,Task.owner_id),(Identity,Identity.user_id),(LoginSession,LoginSession.user_id),(Feedback,Feedback.user_id)]:
                    s.execute(delete(model).where(column == user.id))
                s.query(UsageEvent).filter(UsageEvent.owner_id==user.id).update({"owner_id":"deleted"})
                s.delete(user)
                s.commit()
            except OSError:
                s.rollback()
        used_avatars=select(User.avatar_id).where(User.avatar_id.is_not(None))
        for unused in s.scalars(select(Asset).where(Asset.kind=="avatar",Asset.created<time.time()-86400,Asset.id.not_in(used_avatars))):
            try:
                (MEDIA / (unused.id+".jpg")).unlink(missing_ok=True)
                s.delete(unused)
            except OSError:
                pass
        s.execute(delete(UsageEvent).where(UsageEvent.created < time.time()-60*86400))
        s.execute(delete(LoginSession).where(LoginSession.refresh_expires < time.time()))
        s.execute(delete(OAuthState).where(OAuthState.expires < time.time()))
        s.commit()
