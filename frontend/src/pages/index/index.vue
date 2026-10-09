<script setup lang="ts">
import { openLogin } from '../../auth'
import FlowHeader from '../../components/FlowHeader.vue'
import { useStudio } from '../../studio'
const {user,source,person,busy,current,config,profile,genders,shapes,labels,refresh,choose,generatePortrait,running,imageUrl,networkError,next,preview}=useStudio()
</script>
<template><view class="shell has-tab"><FlowHeader :step="1" title="先选择你的人像" subtitle="上传全身照，或创建一位 AI 模特"/><view v-if="networkError" class="notice"><text>{{networkError}}</text><text class="link" @click="refresh">重试连接</text></view>   <view v-if="!user" class="card welcome"><text>登录后保存你的专属衣橱</text><text class="muted">人像和试穿记录仅自己可见</text><button class="primary" @click="openLogin()">微信快捷登录</button></view><view class="card"><view class="title"><text>01</text> 选择你的人像</view>
    <view class="segments"><text :class="{selected:source==='upload'}" @click="source='upload'">上传照片</text><text :class="{selected:source==='ai'}" @click="source='ai'">随机 AI 人像</text></view>
    <view v-if="person" class="portrait"><image :src="imageUrl(person)" mode="aspectFit" @click="preview(person)"/><text class="remove" @click="person=undefined">移除</text></view>
    <view v-else class="empty portrait-empty" @click="source==='upload'&&!busy&&choose('person')"><text class="plus">＋</text><text>{{source==='upload'?'上传正面全身照':'无需上传，创建专属 AI 模特'}}</text><text class="muted">单人 · 全身完整 · 光线清晰</text></view>
    <button v-if="source==='upload'&&person" class="secondary" :disabled="busy" @click="choose('person')">更换照片</button>
    <view class="fields"><view><text>身高 / cm</text><input type="digit" v-model="profile.height"/></view><view><text>体重 / kg</text><input type="digit" v-model="profile.weight"/></view></view>
    <view class="fields"><view><text>人像性别</text><picker :range="genders" @change="profile.gender=genders[Number($event.detail.value)]"><view class="pick">{{profile.gender}}⌄</view></picker></view><view><text>体型</text><picker :range="shapes" @change="profile.shape=shapes[Number($event.detail.value)]"><view class="pick">{{profile.shape}}⌄</view></picker></view></view>
    <view v-if="source==='ai'" class="fields"><view><text>年龄 / 岁（18～80）</text><input type="number" v-model="profile.age"/></view></view>
    <text class="muted explanation">参数用于 AI 人像生成；上传照片试穿以照片体型为准。请使用本人或已获授权的照片；生成时图片将发送至阿里云处理。</text>
    <button v-if="source==='ai'" class="secondary" :disabled="busy||running()" @click="generatePortrait">✦ {{busy?'正在提交…':person?'换一位 AI 模特':'生成随机 AI 人像'}}</button>
    <text v-if="source==='ai'" class="muted">身高、体重和体型会转换为外形描述，但不能精确复刻实际身材。修改参数后需重新生成人像，万相模型单独计费。</text>
   </view>
<view v-if="current?.kind==='portrait'&&!current.result" class="card waiting"><text>{{labels[current.status]}}</text><text class="muted">{{current.error||'人像生成中，请稍候；离开后仍会继续。'}}</text></view><view class="footer-space"/><view class="action"><view><text class="price">第 1 步 / 共 3 步</text><text class="muted">人像和参数会自动保存</text></view><button class="primary" :disabled="busy||running()||!person" @click="next">下一步 · 选择服装</button></view></view></template>
