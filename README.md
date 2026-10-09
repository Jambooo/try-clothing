# 衣见 AI 1.0.0

uni-app + Vue 3 + Python FastAPI + SQLite 的 AI 人像与服饰试穿应用，使用阿里云 aitryon-plus。

## 当前功能

- 「试衣间 / 我的」双 Tab，白色与浅蓝色主题。
- 人像 → 服饰 → 预览三个独立步骤；上传人像或按外形参数随机生成。
- 微信快捷登录代码接入、服务端身份验证与用户素材隔离。
- 衣橱搜索/分类/收藏/改名、试穿记录与结果保存。
- 会话续期、退出、账号注销、数据导出、帮助反馈及隐私入口。
- 任务幂等、进度恢复、排队取消、生成额度保护、图片签名访问。

## 快速开始

1. 安装 Python 3.10+ 和 Node.js 22.12+。
2. 复制 backend/.env.example 为 backend/.env，填写 DASHSCOPE_API_KEY。
3. 在根目录分别运行 ./start-backend.ps1 和 ./start-frontend.ps1。
4. 打开 http://localhost:5173，进入「我的」登录。没有微信凭据时使用「本机开发登录」体验。

后端地址由 frontend/src/app-config.ts 或 frontend/.env.local 的 VITE_API_BASE_URL 配置，界面不提供连接设置。

微信 AppID / AppSecret 只在 backend/.env 配置；小程序/App 客户端只填写公开 AppID。配置模板不含密钥，Git 忽略所有实际环境文件、数据库与私人图片。不要把密钥写入 VITE_* 变量。

旧 Demo 数据在账号迁移后保留于 local-developer；不分配给微信首次登录用户。

## 文档

- [使用、微信接入、部署与发布边界](docs/APP.md)
- [功能覆盖](docs/FEATURES.md)

微信代码接入完成不等于微信实机登录已验证；项目仍需真实凭据、域名和平台配置。H5、微信小程序可构建，App 需 HBuilderX 打包。当前使用单后端进程；支付、复杂工单流转、通知及分布式部署未实现；基础运营管理及反馈回复已接入。
