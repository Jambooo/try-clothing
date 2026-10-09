"""Operational metadata only; administrators do not bypass photo ownership."""
import time
from datetime import datetime,timezone,timedelta
from fastapi import APIRouter,Depends,HTTPException,Query
from pydantic import BaseModel,Field
from sqlalchemy import select,func,delete
from sqlalchemy.orm import Session
from db import engine,User,Task,Asset,Feedback,UsageEvent,LoginSession,task_lock
from auth import current_user,is_admin
router=APIRouter(prefix="/api/admin",tags=["operations"])

def administrator(user:User=Depends(current_user)):
    if not is_admin(user):
        raise HTTPException(403,"没有管理权限")
    return user

def feedback_data(item):
    return {"id":item.id,"content":item.content,"status":item.status,"reply":item.reply,"created":item.created,"replied_at":item.replied_at}

@router.get("/overview")
def overview(user:User=Depends(administrator)):
    start=datetime.now(timezone(timedelta(hours=8))).replace(hour=0,minute=0,second=0,microsecond=0).timestamp()
    with Session(engine) as s:
        return {"users":s.scalar(select(func.count()).select_from(User).where(User.deleted==False)),"assets":s.scalar(select(func.count()).select_from(Asset)),"active_tasks":s.scalar(select(func.count()).select_from(Task).where(Task.status.in_(["queued","running","saving"]))),"failed_tasks":s.scalar(select(func.count()).select_from(Task).where(Task.status=="failed")),"today_requests":s.scalar(select(func.count()).select_from(UsageEvent).where(UsageEvent.created>=start)),"pending_feedback":s.scalar(select(func.count()).select_from(Feedback).where(Feedback.status=="new"))}

@router.get("/feedback")
def feedback(offset:int=Query(0,ge=0),user:User=Depends(administrator)):
    with Session(engine) as s:
        return [dict(feedback_data(item),user_id=item.user_id) for item in s.scalars(select(Feedback).order_by(Feedback.created.desc()).offset(offset).limit(30))]

class Reply(BaseModel):
    reply:str=Field(min_length=1,max_length=1000)

@router.patch("/feedback/{key}")
def reply_feedback(key:str,body:Reply,user:User=Depends(administrator)):
    if not body.reply.strip():raise HTTPException(422,"回复不能为空")
    with task_lock,Session(engine) as s:
        item=s.get(Feedback,key)
        if not item:raise HTTPException(404,"反馈不存在")
        item.reply=body.reply.strip()
        item.status="replied"
        item.replied_at=time.time()
        s.commit()
        return feedback_data(item)

@router.get("/users")
def users(offset:int=Query(0,ge=0),user:User=Depends(administrator)):
    with Session(engine) as s:
        return [{"id":u.id,"nickname":u.nickname,"disabled":u.disabled,"created":u.created} for u in s.scalars(select(User).where(User.deleted==False).order_by(User.created.desc()).offset(offset).limit(30))]

class UserStatus(BaseModel):
    disabled:bool

@router.patch("/users/{key}")
def user_status(key:str,body:UserStatus,user:User=Depends(administrator)):
    if key==user.id:raise HTTPException(422,"不能停用当前管理员账号")
    with task_lock,Session(engine) as s:
        account=s.get(User,key)
        if not account or account.deleted:raise HTTPException(404,"用户不存在")
        if is_admin(account):raise HTTPException(422,"管理员权限需通过服务器配置管理")
        account.disabled=body.disabled
        if body.disabled:s.execute(delete(LoginSession).where(LoginSession.user_id==key))
        s.commit()
    return {"updated":True}

@router.get("/tasks")
def tasks(offset:int=Query(0,ge=0),user:User=Depends(administrator)):
    with Session(engine) as s:
        return [{"id":t.id,"user_id":t.owner_id,"kind":t.kind,"status":t.status,"error":t.error,"created":t.created} for t in s.scalars(select(Task).order_by(Task.created.desc()).offset(offset).limit(30))]
