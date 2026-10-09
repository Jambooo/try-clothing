<script setup lang="ts">
import FlowHeader from '../../components/FlowHeader.vue'
import { user,logout,deleteAccount,ensureLogin } from '../../auth'
import { request } from '../../api'
import { ref } from 'vue'
const busy=ref(false)
async function exportData(){if(busy.value||!ensureLogin())return;busy.value=true;try{const data=await request<any>('/api/me/export');
 // #ifdef H5
 const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download='yijian-data.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),10000)
 // #endif
 // #ifndef H5
 uni.setClipboardData({data:JSON.stringify(data),success:()=>uni.showToast({title:'数据已复制',icon:'none'})})
 // #endif
 }catch(e:any){uni.showToast({title:e.message,icon:'none'})}finally{busy.value=false}}
function copyId(){uni.setClipboardData({data:user.value?.id||''})}
function policy(){uni.navigateTo({url:'/pages/policy/index'})}
</script>
<template>
<view class="shell"><FlowHeader title="账号与隐私" subtitle="管理登录设备与个人数据" :back="true"/><view class="card"><text class="user-name">{{user?.nickname||'未登录'}}</text><text class="muted" @click="copyId">账号 ID：{{user?.id}} · 点击复制</text><text class="muted explanation">你的素材和记录按账号保存，其他用户无法通过应用访问。</text><button class="secondary" :disabled="busy" @click="exportData">导出我的数据</button><text class="muted">导出个人资料及素材、任务清单；图片请在预览中另行保存。小程序与 App 当前复制清单到剪贴板。</text><button class="secondary" @click="logout(true)">退出所有设备</button><button class="secondary" @click="policy">用户协议与隐私说明</button></view><view class="card"><text class="title">注销账号</text><text class="muted explanation">注销将停用账号并清理你的图片和记录，无法恢复。进行中的任务需先结束或取消。</text><button class="danger" @click="deleteAccount">注销账号并删除数据</button></view></view>
</template>
