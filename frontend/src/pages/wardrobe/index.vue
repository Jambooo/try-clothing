<script setup lang="ts">
import { onShow } from '@dcloudio/uni-app'
import FlowHeader from '../../components/FlowHeader.vue'
import { useStudio } from '../../studio'
const {wardrobe,wardrobeMore,assetFilter,search,favoritesOnly,searchWardrobe,pickAsset,preview,imageUrl,loading,removeAsset,toggleFavorite,renameAsset}=useStudio()
function filter(id:string){assetFilter.value=id;searchWardrobe()}
onShow(()=>searchWardrobe())
</script>
<template>
<view class="shell"><FlowHeader title="我的衣橱" subtitle="保存素材，让下一次搭配更轻松" :back="true"/>
 <view class="card"><input v-model="search" placeholder="搜索素材名称" confirm-type="search" @confirm="searchWardrobe()"/><view class="row"><button class="secondary" :disabled="loading" @click="searchWardrobe()">搜索</button><text class="link" @click="favoritesOnly=!favoritesOnly;searchWardrobe()">{{favoritesOnly?'查看全部':'只看收藏'}}</text></view><view class="filter-list"><text v-for="f in [{id:'all',name:'全部'},{id:'person',name:'人像'},{id:'top',name:'上装'},{id:'bottom',name:'下装'},{id:'dress',name:'连衣裙'},{id:'result',name:'效果图'}]" :key="f.id" :class="{selected:assetFilter===f.id}" @click="filter(f.id)">{{f.name}}</text></view>
 <view class="grid"><view v-for="a in wardrobe.filter(x=>x.kind!=='avatar')" :key="a.id" @click="a.kind==='result'?preview(a):pickAsset(a)"><image :src="imageUrl(a)" mode="aspectFit"/><text>{{a.name}}</text><view class="row"><text class="link" @click.stop="toggleFavorite(a)">{{a.favorite?'★ 已收藏':'☆ 收藏'}}</text><text class="link" @click.stop="renameAsset(a)">改名</text><text class="link" @click.stop="removeAsset(a)">删除</text></view></view></view>
 <view v-if="!wardrobe.length" class="waiting">{{loading?'正在加载…':'暂无符合条件的素材，试试上传一件新服饰。'}}</view><button v-if="wardrobeMore" class="secondary" :disabled="loading" @click="searchWardrobe(true)">{{loading?'加载中…':'加载更多'}}</button></view></view>
</template>
