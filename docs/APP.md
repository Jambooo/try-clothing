# 衣见 AI 1.0.0 · 使用与部署

## 导航和流程

底部仅包含「试衣间」「我的」。试衣间保留三个独立步骤：人像 → 服装 → 预览；详情页有返回入口。「我的」包含个人资料、衣橱、试穿记录、账号管理、帮助反馈和协议说明。界面使用白色、浅蓝色。

连接设置已删除。开发者在 `frontend/src/app-config.ts` 或 `frontend/.env.local` 的 `VITE_API_BASE_URL` 配置公开后端地址，复制 `.env.example` 可作为模板。H5 开发默认当前电脑主机名:8000，生产默认同源 `/api-backend`；小程序和 App 构建前必须设置部署的 HTTPS 地址。旧的本地 apiBase/apiToken 不再读取。

阿里云 Key 与微信 AppSecret 只放在 `backend/.env`，从 `.env.example` 复制需要的配置项。不要向 VITE_* 写入秘密，该前缀会被打包进前端。Git 忽略环境文件、数据库、媒体、签名秘密和构建文件，只提交空值模板。

## 微信登录配置

| 运行端 | 前端入口 | 后端配置 |
| --- | --- | --- |
| 微信小程序 | uni.login 获取 code | WECHAT_MINI_APPID / WECHAT_MINI_SECRET |
| 微信内 H5 | 公众号网页授权 | WECHAT_H5_APPID / WECHAT_H5_SECRET / WECHAT_H5_REDIRECT_URI |
| 普通浏览器 | 开放平台网站应用扫码授权 | WECHAT_WEB_APPID / WECHAT_WEB_SECRET / WECHAT_WEB_REDIRECT_URI |
| 原生 App | uni.login onlyAuthorize 获取 code | WECHAT_APP_APPID / WECHAT_APP_SECRET |

所有 code 由后端向微信兑换，不信任客户端传入的 OpenID，也不把 AppSecret 或微信 session_key 发回前端。OAuth state 一次性、10 分钟过期，并绑定浏览器保存的随机验证字符串。授权回调用 HTTPS 地址且不带 hash，例如 `https://域名/`；必须在微信平台配置相应授权域名和能力。小程序在 manifest.json 填写同一 AppID，配置合法请求/下载域名。App 需在 HBuilderX 配置微信 OAuth SDK、AppID、平台要求的签名和 Universal Links，自定义基座或打包后联调；AppSecret 仍只放后端。

微信凭据未配置时会显示登录尚未开通，不伪造微信登录。开发时本机可使用「本机开发登录」；必须是 loopback 来源且 APP_ENV 不是 production，ENABLE_DEV_LOGIN=true。生产 compose 使用 APP_ENV=production，代码强制禁用开发入口。没有现成微信账号也可先在本机体验。

跨微信端身份只在微信返回经验证的 UnionID 时合并；缺少 UnionID 的独立应用身份不会强行绑定。要跨端共享账号，将各端应用绑定到同一微信开放平台并联调 UnionID 返回条件。

## 用户数据及会话

服务端保存会话 token 的 SHA256 摘要，访问令牌有效 12 小时，刷新令牌有效 30 天且使用后轮换。支持退出当前或全部设备。素材、任务、导出和删除均校验所属用户，生成结果继承任务所属用户。后台配置固定单 worker，SQLite 与进程内锁保障当前部署的幂等和取消边界。

迁移 003 把旧 Demo 数据分配给 local-developer 本地账号。不会自动分配给第一个微信用户。本机开发登录可继续查看旧数据。将旧数据迁入正式账号需要运营者在备份后显式迁移 owner_id，不提供可被用户冒领的接口。

图片使用 24 小时有效签名链接，签名密钥保存在环境变量或 backend/data/.media-secret；签名链接持有者在有效期内可访问，切勿公开转发私人链接。多用户版本只允许 temporary 上传模式，阿里云取图不依赖 ngrok。后端仍把图片发送至百炼临时存储用于生成。

衣橱支持服务端搜索、分类、分页、收藏和改名；保留原图及输出。图片被记录引用时拒绝删除；删除记录不会自动删除素材。排队任务可取消，已开始的模型任务暂不能取消。失败重试回到搭配页确认后才创建新任务。

账号注销立即停用并撤销会话；后台持续重试清理图片、记录、身份及反馈，进行中任务需先结束。请求计数匿名保留不超过 60 天。设备退出/账号切换时清理登录数据、照片草稿和任务引用。导出提供资料、素材和任务 JSON 清单；图片独立保存，移动端当前将清单复制到剪贴板。

## 额度与成本保护

默认每人每日人像 10 次、试穿 20 次，所有用户合计每日 200 次，每用户最多一个活动任务，全局最多五个活动任务。计数包括失败和取消请求，独立于任务历史；删除记录不能恢复额度。参数在后端环境文件调整，按上海时区每日零点重置。设置素材单用户/全局上限，反馈每日最多 5 条；登录接口有每 IP 每分钟限流。

试穿 ¥0.50/张；单件保留服饰或整套提取上衣会额外调用分割，¥0.004/次；人像按万相实际账单。页面提示是模型费用说明，不包含支付实现。使用上限为请求额度，不能直接当成实际已扣费用。

## 本机启动、构建与部署

运行 `./start-backend.ps1` 和 `./start-frontend.ps1`，后端脚本会运行 Alembic，保留原数据库与媒体。端口 8000、5173。

使用 Node 22.12 以上在 frontend 执行 `npm run build:h5`、`npm run build:mp-weixin`。在微信开发者工具导入 dist/build/mp-weixin。App 在 HBuilderX 配置 SDK、权限后打包，不在 Vite 构建命令中模拟实机认证。

Docker：先构建 H5，然后根目录 `docker compose up -d --build`，端口 8080。生产绑定自己的 HTTPS 域名、微信授权回调域名。后端只在内部网络，data 映射宿主机，启动自动执行迁移。不要同时启动两个后端或多个 Uvicorn workers 访问同一数据库；高并发上线需要改独立任务队列与数据库。

停机备份 backend/data 全目录，包括数据库、媒体与 .media-secret。升级前备份；恢复时一起恢复，不重建数据库。清理后仍需按运营方备份保留策略处理旧备份。

基础运营管理支持统计、用户停用/恢复、任务状态查看、反馈回复；用户可在帮助反馈页查看回复。配置 ADMIN_USER_IDS 为应用用户 ID 列表；开发环境的 local-developer 为管理员，生产不默认授予权限。管理员不会绕过照片所属用户限制。不包含复杂工单流转或通知推送系统。

## 发布边界

支付除外，现已补齐基础用户身份、数据隔离、个人资料、登录续期、注销、素材管理、收藏、搜索、分页、任务状态与恢复、取消、导出、反馈和协议入口。

正式发布还需申请并配置微信各端能力、真实联调、HTTPS 和小程序域名、App 打包权限与商店审核，运营者补充主体/联系方式/备份期限等真实协议信息。声明已具备功能不代表已经通过微信审核或完成实机授权联调。复杂工单流转、第三方通知和分布式扩容是后续运营规模相关的扩展，不宣称完成。

## 参考文档

- https://uniapp.dcloud.net.cn/api/plugins/login.html
- https://developers.weixin.qq.com/miniprogram/dev/OpenApiDoc/user-login/code2Session.html
- https://developers.weixin.qq.com/doc/offiaccount/OA_Web_Apps/Wechat_webpage_authorization.html
- https://developers.weixin.qq.com/doc/oplatform/Website_App/WeChat_Login/Wechat_Login.html
