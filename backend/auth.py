"""WeChat code exchange and revocable, hashed application sessions."""
import hashlib
import os
import secrets
import time
import uuid
from collections import defaultdict, deque
from urllib.parse import urlencode, urlparse
import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from db import User, Identity, LoginSession, OAuthState, Asset, engine, asset_data, task_lock

router = APIRouter(prefix="/api/auth", tags=["accounts"])
CONSENT_VERSION = "2026-10-09"
ACCESS_SECONDS = 12 * 3600
REFRESH_SECONDS = 30 * 86400
_rates = defaultdict(deque)

def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

def limit_login(request):
    key = request.client.host if request.client else "unknown"
    now = time.time()
    with task_lock:
        for stale in list(_rates):
            if not _rates[stale] or _rates[stale][-1] < now - 60:
                del _rates[stale]
        bucket = _rates[key]
        while bucket and bucket[0] < now - 60:
            bucket.popleft()
        if len(bucket) >= 20:
            raise HTTPException(429, "登录操作过于频繁，请稍后重试")
        bucket.append(now)

def is_admin(user):
    ids={value.strip() for value in os.getenv("ADMIN_USER_IDS", "").split(",") if value.strip()}
    if os.getenv("APP_ENV","development")!="production":
        ids.add("local-developer")
    return user.id in ids

def user_data(user, session):
    avatar = session.get(Asset, user.avatar_id) if user.avatar_id else None
    return {"id":user.id,"is_admin":is_admin(user),"nickname":user.nickname,"avatar":asset_data(avatar) if avatar and avatar.owner_id == user.id else None,"profile":user.profile,"created":user.created,"consent_version":user.consent_version}

def current_user(authorization: str = Header(default="")):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "请先登录")
    with Session(engine) as s:
        login = s.scalar(select(LoginSession).where(LoginSession.token_hash == digest(authorization[7:]), LoginSession.expires > time.time()))
        user = s.get(User, login.user_id) if login else None
        if not user or user.deleted or user.disabled:
            raise HTTPException(401, "登录已过期，请重新登录")
        s.expunge(user)
        return user

def consent(version):
    if version != CONSENT_VERSION:
        raise HTTPException(422, "请阅读并同意当前用户协议和隐私说明")

def issue(user, session, old=None):
    access, refresh = secrets.token_urlsafe(40), secrets.token_urlsafe(48)
    now = time.time()
    record = old or LoginSession(id=uuid.uuid4().hex,user_id=user.id)
    record.token_hash=digest(access)
    record.refresh_hash=digest(refresh)
    record.expires=now+ACCESS_SECONDS
    record.refresh_expires=now+REFRESH_SECONDS
    if not old:
        previous=list(session.scalars(select(LoginSession).where(LoginSession.user_id==user.id).order_by(LoginSession.created.desc())))
        for expired in previous[9:]:
            session.delete(expired)
        session.add(record)
    session.commit()
    return {"access_token":access,"refresh_token":refresh,"expires_at":record.expires,"user":user_data(user,session)}

def credentials(channel):
    prefixes={"mini":"WECHAT_MINI","h5":"WECHAT_H5","web":"WECHAT_WEB","app":"WECHAT_APP"}
    prefix=prefixes[channel]
    appid,secret=os.getenv(prefix+"_APPID",""),os.getenv(prefix+"_SECRET","")
    if not appid or not secret:
        raise HTTPException(503, "微信登录暂未开通，请稍后再试")
    return appid,secret

def ready(channel):
    prefix={"mini":"WECHAT_MINI","h5":"WECHAT_H5","web":"WECHAT_WEB","app":"WECHAT_APP"}[channel]
    return bool(os.getenv(prefix+"_APPID") and os.getenv(prefix+"_SECRET") and (channel in ["mini","app"] or os.getenv(prefix+"_REDIRECT_URI")))

def dev_allowed(request):
    if os.getenv("APP_ENV","development") == "production" or os.getenv("ENABLE_DEV_LOGIN","true").lower() != "true":
        return False
    if not request.client or request.client.host not in ["127.0.0.1","::1","localhost","testclient"]:
        return False
    origin=request.headers.get("origin")
    if origin and origin not in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","):
        return False
    return True

@router.get("/config")
def configuration(request: Request):
    return {"wechat":{c:ready(c) for c in ["mini","h5","web","app"]},"dev_login":dev_allowed(request),"consent_version":CONSENT_VERSION}

class Accepted(BaseModel):
    accepted_version: str

@router.post("/dev-login")
def developer_login(body: Accepted, request: Request):
    limit_login(request)
    if not dev_allowed(request):
        raise HTTPException(403, "开发登录仅在本机开发环境可用")
    consent(body.accepted_version)
    with task_lock, Session(engine) as s:
        user=s.get(User,"local-developer")
        if not user:
            user=User(id="local-developer",nickname="本地开发者",profile={},consent_version=CONSENT_VERSION)
            s.add(user)
        if user.deleted:
            raise HTTPException(409, "账号数据清理中，请稍后再试")
        if user.disabled:
            raise HTTPException(403,"账号已停用，请通过部署运营者联系处理")
        user.consent_version=CONSENT_VERSION
        return issue(user,s)

class Start(Accepted):
    channel: str = Field(pattern="^(h5|web)$")
    challenge: str = Field(pattern="^[a-f0-9]{64}$")

@router.post("/wechat/start")
def start_oauth(body: Start, request: Request):
    limit_login(request)
    consent(body.accepted_version)
    appid,_=credentials(body.channel)
    prefix="WECHAT_H5" if body.channel=="h5" else "WECHAT_WEB"
    redirect=os.getenv(prefix+"_REDIRECT_URI","")
    if urlparse(redirect).scheme != "https" or not urlparse(redirect).netloc or urlparse(redirect).fragment:
        raise HTTPException(503, "微信授权回调地址尚未正确配置")
    state=secrets.token_hex(24)
    with task_lock, Session(engine) as s:
        s.execute(delete(OAuthState).where(OAuthState.expires < time.time()))
        s.add(OAuthState(state_hash=digest(state),channel=body.channel,challenge=body.challenge,expires=time.time()+600))
        s.commit()
    base="https://open.weixin.qq.com/connect/oauth2/authorize" if body.channel=="h5" else "https://open.weixin.qq.com/connect/qrconnect"
    params={"appid":appid,"redirect_uri":redirect,"response_type":"code","scope":"snsapi_base" if body.channel=="h5" else "snsapi_login","state":state}
    return {"url":base+"?"+urlencode(params)+"#wechat_redirect","state":state}

class WeChatLogin(Accepted):
    channel: str = Field(pattern="^(mini|h5|web|app)$")
    code: str = Field(min_length=1,max_length=512)
    state: str | None = Field(default=None,max_length=128)
    verifier: str | None = Field(default=None,max_length=128)

@router.post("/wechat")
async def wechat_login(body: WeChatLogin, request: Request):
    limit_login(request)
    consent(body.accepted_version)
    appid,secret=credentials(body.channel)
    if body.channel in ["h5","web"]:
        with task_lock, Session(engine) as s:
            state=s.get(OAuthState,digest(body.state or ""))
            if not state or state.expires < time.time() or state.channel != body.channel or not secrets.compare_digest(state.challenge,digest(body.verifier or "")):
                raise HTTPException(400, "微信授权状态无效，请重新发起登录")
            s.delete(state)
            s.commit()
    endpoint="/sns/jscode2session" if body.channel=="mini" else "/sns/oauth2/access_token"
    params={"appid":appid,"secret":secret,"grant_type":"authorization_code", "js_code" if body.channel=="mini" else "code":body.code}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response=await client.get("https://api.weixin.qq.com"+endpoint,params=params)
            response.raise_for_status()
            data=response.json()
    except (httpx.HTTPError,ValueError):
        # Never include HTTP URLs in errors: query parameters contain AppSecret.
        raise HTTPException(503, "微信服务连接异常，请重新登录")
    if data.get("errcode") or not data.get("openid"):
        raise HTTPException(400, "微信登录凭证已失效，请重新授权")
    provider_key=appid+":"+data["openid"]
    unionid=data.get("unionid")
    with task_lock, Session(engine) as s:
        identity=s.scalar(select(Identity).where(Identity.provider_key==provider_key))
        user=s.get(User,identity.user_id) if identity else None
        if user and user.deleted:
            raise HTTPException(409, "账号数据清理中，请稍后再试")
        if not user and unionid:
            user=s.scalar(select(User).where(User.unionid==unionid,User.deleted==False))
        if not user:
            user=User(id=uuid.uuid4().hex,nickname="衣见用户",profile={},unionid=unionid,consent_version=CONSENT_VERSION)
            s.add(user)
            s.flush()
        if not identity:
            s.add(Identity(id=uuid.uuid4().hex,user_id=user.id,provider_key=provider_key))
        if unionid and not user.unionid:
            user.unionid=unionid
        if user.disabled:
            raise HTTPException(403,"账号已停用，请通过部署运营者联系处理")
        user.consent_version=CONSENT_VERSION
        return issue(user,s)

class Refresh(BaseModel):
    refresh_token: str = Field(min_length=20,max_length=256)

@router.post("/refresh")
def refresh_login(body: Refresh, request: Request):
    limit_login(request)
    with task_lock, Session(engine) as s:
        record=s.scalar(select(LoginSession).where(LoginSession.refresh_hash==digest(body.refresh_token),LoginSession.refresh_expires > time.time()))
        user=s.get(User,record.user_id) if record else None
        if not user or user.deleted or user.disabled:
            raise HTTPException(401, "登录已过期，请重新登录")
        return issue(user,s,record)

@router.post("/logout")
def logout(user: User = Depends(current_user), authorization: str = Header(default="")):
    with task_lock, Session(engine) as s:
        s.execute(delete(LoginSession).where(LoginSession.user_id==user.id,LoginSession.token_hash==digest(authorization[7:])))
        s.commit()
    return {"logged_out":True}

@router.post("/logout-all")
def logout_all(user: User = Depends(current_user)):
    with task_lock, Session(engine) as s:
        s.execute(delete(LoginSession).where(LoginSession.user_id==user.id))
        s.commit()
    return {"logged_out":True}
