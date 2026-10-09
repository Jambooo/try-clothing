import asyncio
import os
import secrets
import time
import uuid
import json
from datetime import datetime, timezone, timedelta
from functools import wraps
from contextlib import asynccontextmanager
from typing import Literal
from fastapi import Query, Depends, FastAPI, File, HTTPException, Header, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import select, func, delete
from sqlalchemy.orm import Session
from db import Base, Asset, Task, MEDIA, engine, asset_data, task_data, save_image, valid_media_signature, User, LoginSession, Feedback, UsageEvent, task_lock
from provider import PUBLIC, worker
from image_upload import UPLOAD_MODE

from auth import current_user, router as auth_router, user_data, CONSENT_VERSION

if UPLOAD_MODE != "temporary":
    raise RuntimeError("多用户版本需要 IMAGE_UPLOAD_MODE=temporary，以保护人像访问")
_task_lock = task_lock

def serialized_create(fn):
    @wraps(fn)
    def call(*args, **kwargs):
        with _task_lock:
            return fn(*args, **kwargs)
    return call


def configured():
    if not os.getenv("DASHSCOPE_API_KEY"):
        raise HTTPException(503, "生成服务暂未开通，请稍后再试")

@asynccontextmanager
async def lifespan(app):
    with Session(engine) as s:
        for t in s.scalars(select(Task).where(Task.status == "running", Task.provider_id.is_(None))):
            t.status = "failed"
            t.error = "后端在提交时重启，状态不确定，请核对百炼控制台后再重试"
        s.commit()
    runner = asyncio.create_task(worker())
    app.state.worker=runner
    yield
    runner.cancel()
    try:
        await runner
    except asyncio.CancelledError:
        pass

app = FastAPI(title="衣见 AI", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
                   allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["Authorization", "Content-Type"])

from admin import router as admin_router, feedback_data
app.include_router(auth_router)
app.include_router(admin_router)

@app.get("/health")
def health():
    runner=getattr(app.state,"worker",None)
    if not runner or runner.done():
        raise HTTPException(503,"后台任务服务未就绪")
    return {"status": "ok"}

@app.get("/api/config")
def config(user: User = Depends(current_user)):
    return {"key_ready": bool(os.getenv("DASHSCOPE_API_KEY")), "public_ready": PUBLIC.startswith("https://"),
            "image_upload_mode": UPLOAD_MODE, "model": "aitryon-plus", "portrait_model": os.getenv("PORTRAIT_MODEL", "wan2.2-t2i-flash")}

@app.get("/media/{filename}")
def media(filename: str, expires: int = 0, signature: str = ""):
    if UPLOAD_MODE != "public" and not valid_media_signature(filename[:-4], expires, signature):
        raise HTTPException(403, "图片访问链接已失效，请刷新页面")
    if len(filename) != 36 or not filename.endswith(".jpg") or any(c not in "0123456789abcdef" for c in filename[:-4]):
        raise HTTPException(404)
    path = MEDIA / filename
    if not path.exists():
        raise HTTPException(404)
    return FileResponse(path, media_type="image/jpeg")

@app.post("/api/assets")
async def upload(kind: Literal["person", "top", "bottom", "dress", "avatar"], file: UploadFile = File(...), user: User = Depends(current_user)):
    raw = await file.read(20 * 1024 * 1024 + 1)
    if len(raw) > 20 * 1024 * 1024:
        raise HTTPException(413, "图片不能超过 20MB")
    try:
        return save_image(raw, kind, "upload", file.filename or "上传图片", owner_id=user.id)
    except ValueError as e:
        raise HTTPException(422, str(e))

@app.get("/api/assets")
def assets(offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), kind: str | None = None, q: str = "", favorite: bool = False, user: User = Depends(current_user)):
    with Session(engine) as s:
        return [asset_data(a) for a in s.scalars(select(Asset).where(Asset.owner_id==user.id, Asset.kind!="avatar" if kind!="avatar" else True, Asset.kind==kind if kind else True, Asset.name.contains(q) if q else True, Asset.favorite==True if favorite else True).order_by(Asset.created.desc(),Asset.id.desc()).offset(offset).limit(limit))]

class Profile(BaseModel):
    height: float = Field(default=168, ge=120, le=220)
    weight: float = Field(default=58, ge=30, le=200)
    age: int = Field(default=25, ge=18, le=80)
    gender: Literal["随机", "女性", "男性"] = "随机"
    shape: Literal["自然", "偏瘦", "匀称", "健壮", "丰满"] = "自然"

class TryOn(BaseModel):
    person: str
    top: str | None = None
    bottom: str | None = None
    dress: bool = False
    preserve: bool = True
    profile: Profile
    request_id: str = Field(min_length=16, max_length=64)

@serialized_create
def create_task(kind, snapshot, key, owner):
    with Session(engine) as s:
        existing = s.get(Task, key)
        if existing:
            if existing.owner_id != owner or existing.kind != kind or existing.snapshot != snapshot:
                raise HTTPException(409, "请求编号已用于其他任务")
            return task_data(existing)
        if len(list(s.scalars(select(Task.id).where(Task.status.in_(["queued", "running", "saving"]))))) >= 5:
            raise HTTPException(429, "已有 5 个任务，请等待完成")
        if s.get(UsageEvent,key):
            raise HTTPException(409,"该请求记录已被删除，请创建新的生成请求")
        owner_user=s.get(User,owner)
        if not owner_user or owner_user.deleted or owner_user.disabled:
            raise HTTPException(401,"请重新登录")
        if s.scalar(select(func.count()).select_from(Task).where(Task.owner_id==owner,Task.status.in_(["queued","running","saving"]))) >= 1:
            raise HTTPException(429,"你已有任务进行中，请等待完成")
        own_assets=s.scalar(select(func.count()).select_from(Asset).where(Asset.owner_id==owner))
        asset_total=s.scalar(select(func.count()).select_from(Asset))
        reservations=s.scalar(select(func.count()).select_from(Task).where(Task.status.in_(["queued","running","saving"])))
        if own_assets>=int(os.getenv("MAX_ASSETS_PER_USER","1000")) or asset_total+reservations>=int(os.getenv("MAX_ASSETS_TOTAL","10000")):
            raise HTTPException(429,"图片存储额度已满，请先清理不需要的素材")
        start=datetime.now(timezone(timedelta(hours=8))).replace(hour=0,minute=0,second=0,microsecond=0).timestamp()
        daily=int(os.getenv("DAILY_PORTRAIT_LIMIT","10") if kind=="portrait" else os.getenv("DAILY_TRYON_LIMIT","20"))
        used=s.scalar(select(func.count()).select_from(UsageEvent).where(UsageEvent.owner_id==owner,UsageEvent.kind==kind,UsageEvent.created>=start))
        if used>=daily:
            raise HTTPException(429,"今天的生成请求额度已用完，请明天再来")
        global_used=s.scalar(select(func.count()).select_from(UsageEvent).where(UsageEvent.created>=start))
        if global_used>=int(os.getenv("GLOBAL_DAILY_LIMIT","200")):
            raise HTTPException(429,"今天的服务生成额度已用完，请明天再来")
        t = Task(id=key, owner_id=owner, kind=kind, snapshot=snapshot, status="queued")
        s.add(t)
        s.add(UsageEvent(id=key,owner_id=owner,kind=kind))
        s.commit()
        return task_data(t)

class Portrait(BaseModel):
    profile: Profile
    request_id: str = Field(min_length=16, max_length=64)

@app.post("/api/portraits")
def portrait(body: Portrait, user: User = Depends(current_user)):
    configured()
    return create_task("portrait", {"profile": body.profile.model_dump()}, body.request_id, user.id)

@app.post("/api/tryon")
@serialized_create
def tryon(body: TryOn, user: User = Depends(current_user)):
    configured()
    if UPLOAD_MODE == "public" and not PUBLIC.startswith("https://"):
        raise HTTPException(503, "请在 backend/.env 配置阿里云可访问的 HTTPS PUBLIC_BASE_URL")
    if not body.top and not body.bottom:
        raise HTTPException(422, "至少选择一件服饰")
    if body.dress and (not body.top or body.bottom):
        raise HTTPException(422, "连衣裙不能同时搭配下装")
    with Session(engine) as s:
        for key, allowed in [(body.person, ["person"]), (body.top, ["dress"] if body.dress else ["top"]), (body.bottom, ["bottom"])]:
            if key:
                a = s.get(Asset, key)
                if not a or a.owner_id != user.id or a.kind not in allowed:
                    raise HTTPException(422, "素材不存在或分类不匹配")
        person = s.get(Asset, body.person)
        person.profile = body.profile.model_dump()
        s.commit()
    return create_task("tryon", body.model_dump(exclude={"request_id"}), body.request_id, user.id)

@app.get("/api/tasks")
def tasks(offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), status: str | None = None, kind: str | None = None, user: User = Depends(current_user)):
    with Session(engine) as s:
        return [task_data(t) for t in s.scalars(select(Task).where(Task.owner_id==user.id, Task.status==status if status else True, Task.kind==kind if kind else True).order_by(Task.created.desc(),Task.id.desc()).offset(offset).limit(limit))]

@app.get("/api/tasks/{key}")
def task(key: str, user: User = Depends(current_user)):
    with Session(engine) as s:
        t = s.get(Task, key)
        if not t or t.owner_id != user.id:
            raise HTTPException(404, "任务不存在")
        return task_data(t)

@app.get("/api/assets/{key}")
def asset(key: str, user: User = Depends(current_user)):
    with Session(engine) as s:
        a = s.get(Asset, key)
        if not a or a.owner_id != user.id:
            raise HTTPException(404, "素材不存在")
        return asset_data(a)

@app.delete("/api/tasks/{key}")
def delete_task(key: str, user: User = Depends(current_user)):
    with _task_lock, Session(engine) as s:
        t = s.get(Task, key)
        if not t or t.owner_id != user.id:
            raise HTTPException(404, "记录不存在")
        if t.status not in ["succeeded", "failed", "canceled"]:
            raise HTTPException(409, "进行中的任务不能删除")
        s.delete(t)
        s.commit()
    return {"deleted": True}

@app.delete("/api/assets/{key}")
def delete_asset(key: str, user: User = Depends(current_user)):
    with _task_lock, Session(engine) as s:
        a = s.get(Asset, key)
        if not a or a.owner_id != user.id:
            raise HTTPException(404, "素材不存在")
        for t in s.scalars(select(Task).where(Task.owner_id==user.id)):
            if t.result_id == key or key in [t.snapshot.get(k) for k in ["person", "top", "bottom"]]:
                raise HTTPException(409, "素材被生成记录引用，请先删除相关记录")
        account=s.get(User,user.id)
        if account.avatar_id==key:
            account.avatar_id=None
        # Remove the file first; failed filesystem removal leaves the DB record intact.
        (MEDIA / (key + ".jpg")).unlink(missing_ok=True)
        s.delete(a)
        s.commit()
    return {"deleted": True}


@app.get("/api/me")
def me(user: User = Depends(current_user)):
    with Session(engine) as s:
        data=user_data(user,s)
        data["stats"]={"assets":s.scalar(select(func.count()).select_from(Asset).where(Asset.owner_id==user.id,Asset.kind!="avatar")),"tryons":s.scalar(select(func.count()).select_from(Task).where(Task.owner_id==user.id,Task.kind=="tryon")),"favorites":s.scalar(select(func.count()).select_from(Asset).where(Asset.owner_id==user.id,Asset.favorite==True))}
        day_start=datetime.now(timezone(timedelta(hours=8))).replace(hour=0,minute=0,second=0,microsecond=0).timestamp()
        data["used"]={kind:s.scalar(select(func.count()).select_from(UsageEvent).where(UsageEvent.owner_id==user.id,UsageEvent.kind==kind,UsageEvent.created>=day_start)) for kind in ["portrait","tryon"]}
        data["limits"]={"portrait":int(os.getenv("DAILY_PORTRAIT_LIMIT","10")),"tryon":int(os.getenv("DAILY_TRYON_LIMIT","20"))}
        return data

class UserEdit(BaseModel):
    nickname: str = Field(min_length=1,max_length=24)
    avatar_id: str | None = None
    profile: Profile | None = None

@app.patch("/api/me")
def edit_me(body: UserEdit, user: User = Depends(current_user)):
    nickname=body.nickname.strip()
    if not nickname:
        raise HTTPException(422,"昵称不能为空")
    with task_lock, Session(engine) as s:
        account=s.get(User,user.id)
        if body.avatar_id:
            avatar=s.get(Asset,body.avatar_id)
            if not avatar or avatar.owner_id!=user.id or avatar.kind!="avatar":
                raise HTTPException(422,"头像素材无效")
        account.nickname=nickname
        if "avatar_id" in body.model_fields_set:
            account.avatar_id=body.avatar_id
        if body.profile:
            account.profile=body.profile.model_dump()
        s.commit()
        return user_data(account,s)

@app.delete("/api/me",status_code=202)
def delete_me(user: User = Depends(current_user)):
    with task_lock, Session(engine) as s:
        if s.scalar(select(func.count()).select_from(Task).where(Task.owner_id==user.id,Task.status.in_(["queued","running","saving"]))):
            raise HTTPException(409,"请先取消排队任务或等待生成任务结束，再注销账号")
        account=s.get(User,user.id)
        account.deleted=True
        account.nickname="已注销"
        account.profile={}
        account.unionid=None
        s.execute(delete(LoginSession).where(LoginSession.user_id==user.id))
        s.commit()
    return {"accepted":True,"message":"账号已停用，服务器将清理账号数据"}

@app.get("/api/me/export")
def export_me(user: User = Depends(current_user)):
    with Session(engine) as s:
        data={"user":user_data(user,s),"assets":[asset_data(a) for a in s.scalars(select(Asset).where(Asset.owner_id==user.id))],"tasks":[task_data(t) for t in s.scalars(select(Task).where(Task.owner_id==user.id))]}
    return Response(json.dumps(data,ensure_ascii=False),media_type="application/json",headers={"Content-Disposition":"attachment; filename=yijian-data.json","Cache-Control":"no-store"})

class AssetEdit(BaseModel):
    name: str | None = Field(default=None,min_length=1,max_length=120)
    favorite: bool | None = None

@app.patch("/api/assets/{key}")
def edit_asset(key: str, body: AssetEdit, user: User = Depends(current_user)):
    with task_lock, Session(engine) as s:
        a=s.get(Asset,key)
        if not a or a.owner_id!=user.id:
            raise HTTPException(404,"素材不存在")
        if body.name is not None:
            if not body.name.strip():
                raise HTTPException(422,"名称不能为空")
            a.name=body.name.strip()
        if body.favorite is not None:
            a.favorite=body.favorite
        s.commit()
        return asset_data(a)

@app.post("/api/tasks/{key}/cancel")
def cancel_task(key: str, user: User = Depends(current_user)):
    with task_lock, Session(engine) as s:
        t=s.get(Task,key)
        if not t or t.owner_id!=user.id:
            raise HTTPException(404,"任务不存在")
        if t.status!="queued" or t.provider_id:
            raise HTTPException(409,"任务已开始生成，暂时无法取消")
        t.status="canceled"
        t.error="你已取消该排队任务"
        s.commit()
        return task_data(t)

class FeedbackBody(BaseModel):
    content: str = Field(min_length=10,max_length=1000)

@app.post("/api/feedback")
def feedback(body: FeedbackBody, user: User = Depends(current_user)):
    with task_lock, Session(engine) as s:
        count=s.scalar(select(func.count()).select_from(Feedback).where(Feedback.user_id==user.id,Feedback.created>time.time()-86400))
        if count>=5:
            raise HTTPException(429,"反馈已收到，今天最多提交 5 条")
        item=Feedback(id=uuid.uuid4().hex,user_id=user.id,content=body.content.strip())
        if len(item.content)<10:
            raise HTTPException(422,"请填写至少 10 个字")
        s.add(item)
        s.commit()
        return {"id":item.id,"received":True}


@app.get("/api/feedback")
def my_feedback(offset:int=Query(0,ge=0),user:User=Depends(current_user)):
    with Session(engine) as s:
        return [feedback_data(f) for f in s.scalars(select(Feedback).where(Feedback.user_id==user.id).order_by(Feedback.created.desc()).offset(offset).limit(30))]
