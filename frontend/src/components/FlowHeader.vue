<script setup lang="ts">
const props=defineProps<{step?:number;title:string;subtitle:string;back?:boolean}>()
function home(){uni.switchTab({url:'/pages/index/index'})}
function back(){if(getCurrentPages().length>1)uni.navigateBack();else uni.switchTab({url:'/pages/mine/index'})}
</script>
<template>
 <view class="header"><view @click="home"><text class="brand">衣见</text><text class="ai"> AI</text></view><text v-if="props.back||(props.step&&props.step>1)" class="link" @click="back">‹ 返回</text></view>
 <view v-if="step" class="steps"><view v-for="(label,i) in ['选择人像','选择服装','试穿预览']" :key="label" :class="{active:step===i+1,done:step>i+1}"><text class="step-number">{{step>i+1?'✓':i+1}}</text><text>{{label}}</text></view></view>
 <view class="page-heading"><text>{{title}}</text><text class="muted">{{subtitle}}</text></view>
</template>
