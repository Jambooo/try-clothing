<script setup lang="ts">
import { onShow } from '@dcloudio/uni-app'
import FlowHeader from '../../components/FlowHeader.vue'
import { user, openLogin, loadMe, logout } from '../../auth'
import { imageUrl } from '../../api'
import { APP_VERSION } from '../../app-config'
function go(name:string){if(['wardrobe','history','profile','account'].includes(name)&&!user.value){openLogin('/pages/'+name+'/index');return};uni.navigateTo({url:'/pages/'+name+'/index'})}
onShow(loadMe)
</script>
<template>
<view class="shell has-tab">
 <FlowHeader title="我的" subtitle="每一次搭配，都从了解自己开始"/>
 <view class="card user-card" @click="user?go('profile'):openLogin()"><image v-if="user?.avatar" class="avatar" :src="imageUrl(user.avatar)" mode="aspectFill"/><view v-else class="avatar avatar-placeholder">{{user?.nickname?.slice(0,1)||'衣'}}</view><view><text class="user-name">{{user?.nickname||'欢迎来到衣见'}}</text><text class="muted">{{user?'查看和编辑个人资料':'微信快捷登录，建立专属衣橱'}}</text></view><text class="link">›</text></view>
 <view class="stats"><view><text>{{user?.stats?.assets||0}}</text><text>衣橱素材</text></view><view><text>{{user?.stats?.tryons||0}}</text><text>试穿记录</text></view><view><text>{{user?.stats?.favorites||0}}</text><text>已收藏</text></view></view>
 <view class="card menu-card"><view class="menu-item" @click="go('wardrobe')"><text>我的衣橱</text><text class="muted">人像、服饰与收藏 ›</text></view><view class="menu-item" @click="go('history')"><text>试穿记录</text><text class="muted">查看生成结果 ›</text></view></view>
 <view class="card menu-card"><view class="menu-item" @click="go('account')"><text>账号与隐私</text><text class="muted">账号管理 ›</text></view><view v-if="user?.is_admin" class="menu-item" @click="go('admin')"><text>运营管理</text><text class="muted">服务概况与反馈处理 ›</text></view><view class="menu-item" @click="go('help')"><text>帮助与反馈</text><text class="muted">使用指南 ›</text></view><view class="menu-item" @click="go('policy')"><text>用户协议与隐私说明</text><text class="muted">›</text></view></view>
 <view v-if="user?.limits" class="card"><text class="muted">今日试穿请求 {{user.used?.tryon||0}} / {{user.limits.tryon}} · 人像请求 {{user.used?.portrait||0}} / {{user.limits.portrait}}</text><text class="muted">额度每日零点重置；按请求计数，不代表成功出图费用。</text></view>
 <button v-if="!user" class="primary" @click="openLogin()">微信快捷登录</button><button v-else class="secondary" @click="logout()">退出登录</button><text class="footnote">衣见 AI · {{APP_VERSION}}</text>
</view>
</template>
