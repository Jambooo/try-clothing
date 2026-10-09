<script setup lang="ts">
import FlowHeader from '../../components/FlowHeader.vue'
import { APP_VERSION } from '../../app-config' 
</script>
<template>
<view class="shell"><FlowHeader title="用户协议与隐私说明" subtitle="版本：2026-10-09" :back="true"/><view class="card help-copy"><text class="title">使用说明</text><text>衣见提供 AI 人像生成与服饰试穿参考。你应拥有上传照片的使用权限，禁止上传侵犯他人权益或违法的内容。请勿将生成图片作为实际尺码、身体测量或商品效果的保证。</text><text>模型生成可能失败、改变细节或偏离参考图。提交生成会调用第三方服务；服务端设置每日请求额度。再次生成可能产生额外模型费用。</text><text class="title">收集哪些信息</text><text>微信登录凭证仅用于服务端向微信验证身份；保存微信标识与应用账号关联。不会自动获取你的手机号、微信昵称或头像。昵称、头像和外形参数由你主动填写。</text><text>应用保存你上传的照片、服饰图片、生成图片、任务状态、搭配参数、收藏与反馈。设备本地保存登录会话和试穿草稿，以便恢复使用。</text><text class="title">图片处理与访问</text><text>生成任务需要将输入图片及相关外形描述发送给阿里云百炼服务处理。第三方服务的处理规则以其现行政策为准。应用使用按账号校验的接口及限时图片链接；链接在有效期内可被持有者访问，请不要公开转发私人图片链接。</text><text class="title">保存、删除与导出</text><text>素材和记录保存在应用服务器，直到你主动删除或注销账号。被任务引用的图片需要先删除相关记录。注销会立即停用登录，并由后台清理图片、任务与反馈；进行中的任务需先结束。</text><text>可以在账号页导出个人资料与数据清单。账号注销后，为保护服务额度，保留不关联原账号的生成请求计数，最长 60 天。服务器备份由部署运营者管理，其保留期限应在正式发布时补充公示。</text><text class="title">反馈与运营信息</text><text>问题可通过“帮助与反馈”提交。本开源项目的正式部署运营者需要在发布前补充主体名称、联系邮箱、备份保留期限及真实适用的隐私政策。当前说明用于项目体验，不替代部署运营者的完整协议。</text><text class="muted">衣见 AI {{APP_VERSION}}</text></view></view>
</template>
