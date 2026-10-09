"""Upload model-bound images to Alibaba's temporary storage for local demos."""
import os
import uuid
import httpx
from db import MEDIA

UPLOAD_MODE = os.getenv("IMAGE_UPLOAD_MODE", "temporary")

async def model_image(client: httpx.AsyncClient, asset_id: str, model: str, base: str, public: str):
    path = MEDIA / (asset_id + ".jpg")
    if not path.is_file():
        raise RuntimeError("输入素材已不存在，请重新上传")
    size = path.stat().st_size
    if not 5120 <= size <= 5 * 1024 * 1024:
        raise RuntimeError("模型输入图片必须为 5KB～5MB，请重新上传更清晰的图片")
    if UPLOAD_MODE == "public":
        return public + "/media/" + asset_id + ".jpg"
    headers = {"Authorization": "Bearer " + os.getenv("DASHSCOPE_API_KEY", "")}
    response = await client.get(base + "/uploads", headers=headers,
                                params={"action": "getPolicy", "model": model})
    if response.is_error:
        raise RuntimeError("百炼临时上传凭证获取失败，请检查地域、模型权限或网络")
    data = response.json().get("data", {})
    required = ["upload_dir", "upload_host", "oss_access_key_id", "signature", "policy",
                "x_oss_object_acl", "x_oss_forbid_overwrite"]
    if not all(k in data for k in required):
        raise RuntimeError("百炼返回的上传凭证不完整")
    filename = uuid.uuid4().hex + ".jpg"
    key = data["upload_dir"].rstrip("/") + "/" + filename
    fields = {
        "OSSAccessKeyId": (None, data["oss_access_key_id"]),
        "Signature": (None, data["signature"]),
        "policy": (None, data["policy"]),
        "x-oss-object-acl": (None, data["x_oss_object_acl"]),
        "x-oss-forbid-overwrite": (None, data["x_oss_forbid_overwrite"]),
        "key": (None, key),
        "success_action_status": (None, "200"),
    }
    # Model credentials are used only for getPolicy; never send the API Key to OSS.
    with path.open("rb") as handle:
        uploaded = await client.post(data["upload_host"],
                                     files={**fields, "file": (filename, handle, "image/jpeg")})
    if uploaded.status_code != 200:
        raise RuntimeError("图片上传至百炼临时存储失败，请检查网络后重试")
    return "oss://" + key
