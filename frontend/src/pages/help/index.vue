<script setup lang="ts">
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import FlowHeader from '../../components/FlowHeader.vue'
import { user,ensureLogin } from '../../auth'
import { request } from '../../api'
const content=ref(''),busy=ref(false),records=ref<any[]>([]),more=ref(false)
async function load(append=false){if(!user.value)return;try{const items=await request<any[]>('/api/feedback?offset='+(append?records.value.length:0));records.value=append?[...records.value,...items]:items;more.value=items.length===30}catch(e:any){uni.showToast({title:e.message,icon:'none'})}}
onShow(()=>load())
async function send(){if(!ensureLogin()||busy.value)return;if(content.value.trim().length<10){uni.showToast({title:'请至少填写 10 个字',icon:'none'});return}busy.value=true;try{await request('/api/feedback','POST',{content:content.value.trim()});content.value='';await load();uni.showToast({title:'反馈已收到'})}catch(e:any){uni.showToast({title:e.message,icon:'none'})}finally{busy.value=false}}
</script>
<template>
<view class="shell"><FlowHeader title="帮助与反馈" subtitle="让每一次试穿更顺利" :back="true"/><view class="card help-copy"><text class="title">如何获得更好的效果？</text><text>人像：正面单人全身照，头顶与双脚完整，双臂不要遮挡衣服。</text><text>服饰：清晰完整的正面平铺图，背景简洁；上装与下装分别上传。</text><text>外形参数：用于生成人像的视觉描述，不能精确复刻真实身体或预测合身尺码。</text><text>生成中：可以离开页面，任务仍会继续。排队时可以取消；提交给模型后暂不能取消。</text><text>失败后：先查看错误提示并调整素材；再次确认生成会创建新请求。每日额度按请求计数，不等于实际账单费用。</text><text>保存图片：H5 打开原图后长按保存；小程序和 App 需要相册权限。</text><text>费用：试穿 ¥0.50/张，服饰分割 ¥0.004/次，人像生成按模型另计，以服务商账单为准。</text></view><view class="card"><text class="title">意见反馈</text><textarea v-model="content" maxlength="1000" placeholder="描述你遇到的问题或建议（10～1000字），请不要填写密码或密钥。"/><text class="muted">{{content.length}} / 1000 · 提交后保存在应用服务端</text><button class="primary" :disabled="busy" @click="send">{{busy?'提交中…':'提交反馈'}}</button></view><view v-if="user" class="card"><text class="title">我的反馈</text><view v-for="item in records" :key="item.id" class="feedback-item"><text>{{item.content}}</text><text class="muted">{{new Date(item.created*1000).toLocaleString()}} · {{item.status==='new'?'等待处理':'已回复'}}</text><view v-if="item.reply" class="feedback-reply"><text>回复：{{item.reply}}</text></view></view><text v-if="!records.length" class="muted">暂无反馈记录</text><button v-if="more" class="secondary" @click="load(true)">加载更多</button></view></view>
</template>
