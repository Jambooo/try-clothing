import asyncio
import logging
import os
import json
import secrets
import time
import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session
from db import Task, User, engine, save_image, update, task_lock, cleanup_accounts
from image_upload import model_image, UPLOAD_MODE
from portrait_prompt import build_portrait_prompt

BASE = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/api/v1").rstrip("/")
PUBLIC = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

def input_url(key):
    return PUBLIC + "/media/" + key + ".jpg"

async def api(client, method, path, body=None, asynchronous=False):
    headers = {"Authorization": "Bearer " + os.getenv("DASHSCOPE_API_KEY", "")}
    if body and "oss://" in json.dumps(body):
        headers["X-DashScope-OssResourceResolve"] = "enable"
    if asynchronous:
        headers["X-DashScope-Async"] = "enable"
    response = await client.request(method, BASE + path, headers=headers, json=body)
    try:
        data = response.json()
    except ValueError:
        raise RuntimeError("阿里云返回非 JSON 响应")
    if response.is_error or data.get("code"):
        if data.get("code") == "InvalidParameter.DataInspection" and "download" in data.get("message", "").lower():
            raise RuntimeError("阿里云未能读取输入图片。请检查临时上传或公网取图链路；原图仍已保存。")
        raise RuntimeError(str(data.get("code", response.status_code)) + ": " + str(data.get("message", "模型请求失败"))[:400])
    return data.get("output", {})

async def process(key):
    with Session(engine) as s:
        t = s.get(Task, key)
        if not t or t.status not in ["queued","running","saving"]:
            return
        owner_id=t.owner_id
        snap, kind, pid, output_url, created = t.snapshot, t.kind, t.provider_id, t.output_url, t.created
    async with httpx.AsyncClient(timeout=90) as client:
        if not pid and not output_url:
            with task_lock, Session(engine) as s:
                task=s.get(Task,key)
                account=s.get(User,owner_id)
                if not task or task.status not in ["queued","running"] or not account or account.deleted:
                    return
                if account.disabled:
                    task.status="canceled"
                    task.error="账号已停用，排队任务已取消"
                    s.commit()
                    return
                task.status="running"
                s.commit()
            if kind == "portrait":
                p = snap["profile"]
                prompt, negative_prompt = build_portrait_prompt(p)
                body = {"model": os.getenv("PORTRAIT_MODEL", "wan2.2-t2i-flash"),
                        "input": {"prompt": prompt, "negative_prompt": negative_prompt},
                        "parameters": {"size": "768*1344", "n": 1, "seed": secrets.randbelow(2147483647)}}
                out = await api(client, "POST", "/services/aigc/text2image/image-synthesis", body, True)
            else:
                inp = {"person_image_url": await model_image(client, snap["person"], "aitryon-plus", BASE, PUBLIC)}
                for field in ["top", "bottom"]:
                    if snap.get(field):
                        inp[field + "_garment_url"] = await model_image(client, snap[field], "aitryon-plus", BASE, PUBLIC)
                # A worn top reference can also contain trousers. Isolate the upper
                # garment so it does not compete with the selected bottom reference.
                if snap.get("top") and snap.get("bottom") and not snap["dress"]:
                    crop = await api(client, "POST", "/services/vision/image-process/process",
                                     {"model": "aitryon-parsing-v1",
                                      "input": {"image_url": await model_image(client, snap["top"], "aitryon-parsing-v1", BASE, PUBLIC)},
                                      "parameters": {"clothes_type": ["upper"]}})
                    urls = crop.get("crop_img_url", [])
                    if not urls or not urls[0]:
                        raise RuntimeError("未能提取上装，请更换清晰完整的上装图，或先单独试穿下装")
                    inp["top_garment_url"] = urls[0]
                if snap["preserve"] and not snap["dress"] and bool(snap.get("top")) != bool(snap.get("bottom")):
                    missing = "bottom" if snap.get("top") else "top"
                    crop = await api(client, "POST", "/services/vision/image-process/process",
                                     {"model": "aitryon-parsing-v1",
                                      "input": {"image_url": await model_image(client, snap["person"], "aitryon-parsing-v1", BASE, PUBLIC)},
                                      "parameters": {"clothes_type": ["lower" if missing == "bottom" else "upper"]}})
                    urls = crop.get("crop_img_url", [])
                    if not urls or not urls[0]:
                        raise RuntimeError("未能分割原服饰，请换一张全身照或关闭保留原服饰")
                    inp[missing + "_garment_url"] = urls[0]
                out = await api(client, "POST", "/services/aigc/image2image/image-synthesis",
                                {"model": "aitryon-plus", "input": inp,
                                 "parameters": {"restore_face": True, "resolution": -1}}, True)
            pid = out.get("task_id")
            if not pid:
                raise RuntimeError("模型未返回任务编号")
            update(key, provider_id=pid)
        if not output_url:
            if time.time() - created > 23 * 3600:
                raise RuntimeError("任务超过查询有效期，请重新创建")
            out = await api(client, "GET", "/tasks/" + pid)
            state = out.get("task_status")
            if state in ["FAILED", "CANCELED", "UNKNOWN"]:
                raise RuntimeError(str(out.get("message", "模型任务失败")))
            if state != "SUCCEEDED":
                return
            results = out.get("results") or []
            output_url = out.get("image_url") or next((r.get("url") for r in results if r.get("url")), None)
            if not output_url:
                raise RuntimeError("模型未返回图片")
            update(key, output_url=output_url, status="saving")
        response = await client.get(output_url)
        response.raise_for_status()
        if len(response.content) > 30 * 1024 * 1024:
            raise RuntimeError("生成图片过大")
        result = save_image(response.content, "person" if kind == "portrait" else "result",
                            "ai", "AI 人像" if kind == "portrait" else "试穿效果", snap.get("profile"), owner_id=owner_id)
        update(key, result_id=result["id"], status="succeeded", error=None)

async def worker():
    while True:
        try:
            with Session(engine) as s:
                keys = list(s.scalars(select(Task.id).where(Task.status.in_(["queued", "running", "saving"])).order_by(Task.created)))
            for key in keys:
                try:
                    await process(key)
                except (httpx.TransportError, httpx.HTTPStatusError):
                    with Session(engine) as s:
                        t = s.get(Task, key)
                        known = bool(t.provider_id or t.output_url)
                        saving = bool(t.output_url)
                    update(key, status=("saving" if saving else "running") if known else "failed",
                           error="网络异常，将继续查询或保存" if known else "提交网络异常，状态不确定；请先核对百炼控制台，避免重复计费")
                except Exception as e:
                    update(key, status="failed", error=str(e)[:500])
            cleanup_accounts()
        except Exception:
            logging.getLogger(__name__).exception("后台任务循环异常，将继续重试")
        await asyncio.sleep(5)
