<script setup lang="ts">
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import FlowHeader from '../../components/FlowHeader.vue'
import { authBusy,authConfig,loadAuthConfig,wechatLogin,devLogin } from '../../auth'
const accepted=ref(false)
function policy(){uni.navigateTo({url:'/pages/policy/index'})}
onShow(loadAuthConfig)
</script>
<template>
<view class="shell"><FlowHeader title="登录衣见" subtitle="用微信开启你的专属试衣间" :back="true"/>
 <view class="card login-card"><view class="login-symbol">衣</view><text class="user-name">搭配灵感，随时回来</text><text class="muted explanation">登录后同步衣橱与试穿记录。不会自动获取微信昵称、头像或手机号。</text><button class="primary" :disabled="authBusy||!authConfig" @click="wechatLogin(accepted)">{{authBusy?'正在登录…':'微信快捷登录'}}</button>
 <button v-if="authConfig?.dev_login" class="secondary" :disabled="authBusy" @click="devLogin(accepted)">本机开发登录</button><text v-if="authConfig?.dev_login" class="muted">开发入口仅限本机，正式环境关闭。</text>
 <checkbox-group @change="accepted=$event.detail.value.length>0"><label class="consent"><checkbox value="accepted" :checked="accepted" color="#428bd6"/><text>我已阅读并同意</text><text class="link" @click.stop="policy">用户协议与隐私说明</text></label></checkbox-group>
 </view></view>
</template>
