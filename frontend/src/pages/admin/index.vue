<script setup lang="ts">
import { ref,reactive } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import FlowHeader from '../../components/FlowHeader.vue'
import { request } from '../../api'
import { user,ensureLogin } from '../../auth'
const view=ref('feedback'),overview=ref<any>(),items=ref<any[]>([]),busy=ref(false),more=ref(false),replies=reactive<Record<string,string>>({})
const hint=(e:any)=>uni.showToast({title:e.message,icon:'none'})
async function load(append=false){if(!ensureLogin()||!user.value?.is_admin||busy.value)return;busy.value=true;try{overview.value=await request('/api/admin/overview');const rows=await request<any[]>('/api/admin/'+view.value+'?offset='+(append?items.value.length:0));items.value=append?[...items.value,...rows]:rows;more.value=rows.length===30;for(const item of rows)if(view.value==='feedback')replies[item.id]=item.reply||''}catch(e){hint(e)}finally{busy.value=false}}
function switchView(value:string){view.value=value;items.value=[];load()}
async function reply(item:any){if(busy.value)return;busy.value=true;try{Object.assign(item,await request('/api/admin/feedback/'+item.id,'PATCH',{reply:replies[item.id]}));uni.showToast({title:'回复已保存'})}catch(e){hint(e)}finally{busy.value=false}}
async function status(item:any){const yes=await new Promise<boolean>(resolve=>uni.showModal({title:item.disabled?'恢复账号？':'停用账号？',content:'停用将撤销登录会话，恢复后用户需重新登录。',success:r=>resolve(r.confirm)}));if(!yes)return;try{await request('/api/admin/users/'+item.id,'PATCH',{disabled:!item.disabled});item.disabled=!item.disabled}catch(e){hint(e)}}
onShow(()=>load())
</script>
<template><view class="shell"><FlowHeader title="运营管理" subtitle="管理服务状态、用户和反馈" :back="true"/><view v-if="!user?.is_admin" class="notice">当前账号没有管理权限</view><view v-else>
 <view v-if="overview" class="card"><view class="stats"><view><text>{{overview.users}}</text><text>用户</text></view><view><text>{{overview.today_requests}}</text><text>今日请求</text></view><view><text>{{overview.active_tasks}}</text><text>进行中</text></view></view><text class="muted">待处理反馈 {{overview.pending_feedback}} · 失败任务 {{overview.failed_tasks}} · 素材总数 {{overview.assets}}</text></view>
 <view class="filter-list"><text v-for="tab in [{id:'feedback',label:'反馈处理'},{id:'users',label:'账号管理'},{id:'tasks',label:'任务状态'}]" :key="tab.id" :class="{selected:view===tab.id}" @click="switchView(tab.id)">{{tab.label}}</text></view>
 <view v-for="item in items" :key="item.id" class="card"><text class="muted">{{new Date(item.created*1000).toLocaleString()}}</text>
 <view v-if="view==='feedback'"><text class="support-content">{{item.content}}</text><text class="muted">{{item.status==='new'?'待处理':'已回复'}}</text><textarea v-model="replies[item.id]" maxlength="1000" placeholder="填写回复，用户可在帮助与反馈查看。"/><button class="secondary" :disabled="busy" @click="reply(item)">保存回复</button></view>
 <view v-else-if="view==='users'"><text class="user-name">{{item.nickname}}</text><text class="muted">{{item.id}}</text><button class="secondary" @click="status(item)">{{item.disabled?'恢复账号':'停用账号'}}</button></view>
 <view v-else><text>{{item.kind==='portrait'?'人像':'试穿'}} · {{item.status}}</text><text class="muted">{{item.id}}</text><text class="error">{{item.error}}</text></view></view>
 <view v-if="!items.length" class="card waiting">{{busy?'加载中…':'暂无记录'}}</view><button v-if="more" class="secondary" :disabled="busy" @click="load(true)">加载更多</button>
 </view></view></template>
