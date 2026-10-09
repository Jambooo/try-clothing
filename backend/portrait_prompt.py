"""Translate body inputs into visual cues, not exact physical measurements."""
import secrets


def build_portrait_prompt(profile):
    height = float(profile["height"])
    weight = float(profile["weight"])
    # A coarse prompt heuristic only; this is not a clinical classification or
    # a guarantee of appearance. Explicit silhouette cues help image generation.
    ratio = weight / ((height / 100) ** 2)
    if ratio >= 35:
        silhouette = "体格非常宽厚、明显大码的成年人，躯干宽厚，腹部明显圆润，腰围较大，上臂粗壮，大腿和小腿丰满"
        avoid = "瘦削身材，苗条身材，纤细腰部，细胳膊细腿，平坦腹部，健美腹肌，沙漏细腰，修长超模身材"
    elif ratio >= 30:
        silhouette = "明显偏胖、丰满宽厚的大码成年人，圆润饱满的腹部，宽厚腰部，丰满上臂，粗壮饱满的大腿，身体有明显脂肪体积"
        avoid = "瘦削身材，苗条身材，纤细腰部，细胳膊细腿，平坦腹部，健美腹肌，沙漏细腰，修长超模身材"
    elif ratio >= 25:
        silhouette = "体格较宽、偏丰满的成年人，腰腹饱满，有自然的腹部弧度，上臂和大腿饱满"
        avoid = "骨感身材，极细腰部，极细手臂，极细腿，健美腹肌，修长超模身材"
    elif ratio < 18.5:
        silhouette = "整体较瘦、轻盈的成年人，躯干较窄，四肢较细，自然健康的外形"
        avoid = "非常宽厚的躯干，极粗壮的四肢，夸张的肌肉，修长超模比例"
    else:
        silhouette = "普通成年人自然体格，躯干和四肢比例协调，无夸张的腰身或肌肉"
        avoid = "极端骨感身材，夸张肌肉，夸张沙漏身材，修长超模比例"
    shape = profile["shape"]
    detail = {
        "自然": "体型和脂肪分布自然",
        "偏瘦": "在该身高体重对应的整体体格基础上，四肢相对轻盈，不改变整体体积",
        "匀称": "身体体积分布均匀，肩腰胯与四肢协调",
        "健壮": "肩膀宽厚，四肢结实，保持该体重对应的身体体积",
        "丰满": "丰满圆润，腰腹饱满，上臂与大腿都有自然软组织体积，不收细腰部",
    }[shape]
    gender = profile["gender"] if profile["gender"] != "随机" else secrets.choice(["女性", "男性"])
    hair = secrets.choice(["自然短发", "整齐中长发", "自然黑发"])
    prompt = (
        f"真实生活摄影，单个成年{gender}，年龄{profile['age']}岁，{silhouette}。{detail}。"
        f"身高约{height:g}厘米，体重约{weight:g}公斤，整体体型必须与上述宽度和体积一致。{hair}。"
        "普通人的身体外形，不美化或改变体型。正面完整全身站立照，标准视角，镜头水平，"
        "头顶和双脚完整入镜，双脚稍微分开，双臂与躯干略微分开以露出腰腹和身体轮廓。"
        "穿单层素色短袖T恤和合身长裤及简洁鞋子，衣服随身体轮廓自然贴合，"
        "不穿宽松外套，不使用遮挡腰腹的配饰。浅灰摄影棚背景，柔和均匀光线，真实自然比例，无文字。"
    )
    negative = "多人，截断脚部，坐姿，交叉手臂，遮挡腰腹，宽松外套，畸形，文字，拉长身体，夸张长腿，" + avoid
    return prompt, negative
