<script setup lang="ts">
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import FlowHeader from '../../components/FlowHeader.vue'
import { user,ensureLogin,loadMe } from '../../auth'
import { request,upload,uploadFile,imageUrl,type Asset,type User } from '../../api'
const nickname=ref(''),avatar=ref<Asset>(),busy=ref(false)
const hint=(e:any)=>uni.showToast({title:e.message,icon:'none'})
async function pickAvatar(){if(busy.value)return;busy.value=true;try{avatar.value=await upload('avatar')}catch(e){hint(e)}finally{busy.value=false}}
async function chooseAvatar(e:any){busy.value=true;try{avatar.value=await uploadFile('avatar',e.detail.avatarUrl)}catch(e){hint(e)}finally{busy.value=false}}
async function save(){if(busy.value||!ensureLogin())return;busy.value=true;try{user.value=await request<User>('/api/me','PATCH',{nickname:nickname.value.trim(),avatar_id:avatar.value?.id||null});uni.setStorageSync('sessionUser',user.value);uni.showToast({title:'资料已更新'});uni.navigateBack()}catch(e){hint(e)}finally{busy.value=false}}
onShow(async()=>{if(!ensureLogin())return;await loadMe();nickname.value=user.value?.nickname||'';avatar.value=user.value?.avatar})
</script>
<template>
<view class="shell"><FlowHeader title="个人资料" subtitle="设置你喜欢的昵称与头像" :back="true"/>
 <view class="card"><view class="avatar-editor"><image v-if="avatar" class="avatar" :src="imageUrl(avatar)" mode="aspectFill"/><view v-else class="avatar avatar-placeholder">衣</view>
 <!-- #ifdef MP-WEIXIN --><button class="secondary" open-type="chooseAvatar" @chooseavatar="chooseAvatar" :disabled="busy">选择头像</button><!-- #endif -->
 <!-- #ifndef MP-WEIXIN --><button class="secondary" @click="pickAvatar" :disabled="busy">更换头像</button><!-- #endif -->
 </view><text class="field-label">昵称</text><input v-model="nickname" type="nickname" maxlength="24" placeholder="请输入昵称"/><text class="muted explanation">头像和昵称由你主动设置，不影响微信账号身份。</text><button class="primary" :disabled="busy||!nickname.trim()" @click="save">{{busy?'正在保存…':'保存资料'}}</button></view></view>
</template>
