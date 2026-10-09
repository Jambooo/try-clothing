import { ref, reactive, watch } from 'vue'
import { onShow, onHide, onUnload } from '@dcloudio/uni-app'
import { user, ensureLogin } from './auth'
import { request, upload, imageUrl, requestId, type Asset, type Task } from './api'

function createStudio(){
 const source=ref('upload'), person=ref<Asset>(), top=ref<Asset>(), bottom=ref<Asset>()
 const category=ref('top'), busy=ref(false), preserve=ref(true), current=ref<Task>(), history=ref<Task[]>([]), library=ref<Asset[]>([])
 const config=ref<any>()
 const profile=reactive({height:168,weight:58,age:25,gender:'随机',shape:'自然'})
 const genders=['随机','女性','男性'], shapes=['自然','偏瘦','匀称','健壮','丰满']
 const search=ref(''), favoritesOnly=ref(false)
 const labels:Record<string,string>={queued:'等待生成',running:'AI 正在生成',saving:'正在保存',succeeded:'已完成',failed:'生成失败',canceled:'已取消'}
 const networkError=ref(''), loading=ref(false), hasMore=ref(true), moreAssets=ref(true), assetFilter=ref('all')
 let timer:ReturnType<typeof setInterval>|undefined
 let polling=false
 const wardrobe=ref<Asset[]>([]), wardrobeMore=ref(true)
 const wardrobeQuery=()=>'?kind='+(assetFilter.value==='all'?'':assetFilter.value)+'&q='+encodeURIComponent(search.value)+'&favorite='+favoritesOnly.value
 async function searchWardrobe(more=false){if(!ensureLogin())return;loading.value=true;try{const items=await request<Asset[]>('/api/assets'+wardrobeQuery()+'&offset='+(more?wardrobe.value.length:0));wardrobe.value=more?[...wardrobe.value,...items]:items;wardrobeMore.value=items.length===50}catch(e){hint(e)}finally{loading.value=false}}
 async function toggleFavorite(a:Asset){try{const result=await request<Asset>('/api/assets/'+a.id,'PATCH',{favorite:!a.favorite});Object.assign(a,result)}catch(e){hint(e)}}
 async function renameAsset(a:Asset){uni.showModal({title:'修改素材名称',editable:true,placeholderText:a.name,success:async r=>{if(!r.confirm)return;try{const result=await request<Asset>('/api/assets/'+a.id,'PATCH',{name:r.content});Object.assign(a,result)}catch(e){hint(e)}}})}
 async function cancelCurrent(){if(!current.value)return;try{active(await request<Task>('/api/tasks/'+current.value.id+'/cancel','POST'))}catch(e){hint(e)}}
 const hint=(e:any)=>uni.showToast({title:e?.message||String(e),icon:'none',duration:3500})
 async function refresh(){if(!user.value){history.value=[];library.value=[];return};loading.value=true;try{const [c,h,l]=await Promise.all([request('/api/config'),request<Task[]>('/api/tasks'),request<Asset[]>('/api/assets')]);config.value=c;history.value=h;library.value=l;for(const selected of [person,top,bottom]){if(selected.value){const selectedId=selected.value.id;const fresh=l.find(a=>a.id===selectedId)||await request<Asset>('/api/assets/'+selectedId);if(selected.value?.id===selectedId)selected.value=fresh}};networkError.value='';hasMore.value=h.length===50;moreAssets.value=l.length===50}catch(e:any){networkError.value=e.message}finally{loading.value=false}}
 async function moreHistory(){if(loading.value||!hasMore.value)return;loading.value=true;try{const items=await request<Task[]>('/api/tasks?offset='+history.value.length);history.value.push(...items);hasMore.value=items.length===50}catch(e){hint(e)}finally{loading.value=false}}
 async function loadMoreAssets(){if(loading.value||!moreAssets.value)return;loading.value=true;try{const items=await request<Asset[]>('/api/assets?offset='+library.value.length);library.value.push(...items);moreAssets.value=items.length===50}catch(e){hint(e)}finally{loading.value=false}}
 function applyPortrait(a:Asset){if(uni.getStorageSync('appliedPortrait')!==a.id){selectPerson(a);uni.setStorageSync('appliedPortrait',a.id)}}
 function selectPerson(a:Asset){person.value=a;source.value=a.source==='ai'?'ai':'upload';if(a.profile?.height)Object.assign(profile,a.profile)}
 async function poll(){
  if(polling||!current.value||['succeeded','failed','canceled'].includes(current.value.status))return
  polling=true
  try{const taskId=current.value.id;const fetched=await request<Task>('/api/tasks/'+taskId);if(current.value?.id!==taskId)return;current.value=fetched;networkError.value=''
   if(current.value.status==='succeeded'){if(current.value.kind==='portrait'&&current.value.result)applyPortrait(current.value.result);await refresh()}
  }catch(e:any){networkError.value=e.message}finally{polling=false}
 }
 async function resume(){if(!user.value)return;await refresh();const id=uni.getStorageSync('activeTask')||history.value.find(t=>['queued','running','saving'].includes(t.status))?.id;if(id&&!uni.getStorageSync('activeTask'))uni.setStorageSync('activeTask',id);if(id)try{const fetched=await request<Task>('/api/tasks/'+id);if(uni.getStorageSync('activeTask')===id){current.value=fetched;if(fetched.kind==='portrait'&&fetched.result)applyPortrait(fetched.result)}}catch(e:any){if(e.status===404){uni.removeStorageSync('activeTask');current.value=undefined}else networkError.value=e.message};await loadOriginal();await poll()}

 function start(){if(timer)clearInterval(timer);void resume();timer=setInterval(poll,5000)}
 function stop(){if(timer){clearInterval(timer);timer=undefined}}
 const stored=user.value?uni.getStorageSync('fittingDraft'):undefined;if(stored&&typeof stored==='object'){source.value=stored.source||'upload';person.value=stored.person;top.value=stored.top;bottom.value=stored.bottom;category.value=stored.category||'top';preserve.value=stored.preserve!==false;Object.assign(profile,stored.profile||{})}
 uni.$on('session-cleared',()=>{stop();person.value=undefined;top.value=undefined;bottom.value=undefined;current.value=undefined;original.value=undefined;library.value=[];history.value=[];wardrobe.value=[];networkError.value='';Object.assign(profile,{height:168,weight:58,age:25,gender:'随机',shape:'自然'})})
 uni.$on('session-ready',()=>{if(user.value?.profile?.height)Object.assign(profile,user.value.profile);start()})
 watch([source,person,top,bottom,category,preserve,profile],()=>uni.setStorageSync('fittingDraft',{source:source.value,person:person.value,top:top.value,bottom:bottom.value,category:category.value,preserve:preserve.value,profile:{...profile}}),{deep:true})
 function go(page:string){const url='/pages/'+page+'/index';if(getCurrentPages().length>=8)uni.reLaunch({url});else uni.navigateTo({url})}
 async function next(){if(!ensureLogin())return;if(busy.value||running())return;busy.value=true;try{valid();if(!person.value)throw new Error('请先上传或生成一张人像');const account=await request<any>('/api/me','PATCH',{nickname:user.value?.nickname,profile:normalized()});if(user.value){user.value.profile=account.profile;uni.setStorageSync('sessionUser',user.value)};go('garments')}catch(e){hint(e)}finally{busy.value=false}}
 function edit(){uni.switchTab({url:'/pages/index/index'})}
 async function snapshotAsset(id?:string){if(!id)return;return library.value.find(a=>a.id===id)||await request<Asset>('/api/assets/'+id)}
 const original=ref<Asset>()
 async function loadOriginal(){original.value=undefined;if(current.value?.kind==='tryon')try{{const taskId=current.value.id;const asset=await snapshotAsset(current.value.snapshot.person);if(current.value?.id===taskId)original.value=asset}}catch(e){hint(e)}}
 function active(t:Task){current.value=t;uni.setStorageSync('activeTask',t.id)}
 async function choose(kind:string){if(!ensureLogin())return;busy.value=true;try{const a=await upload(kind);if(kind==='person')selectPerson(a);else if(kind==='bottom')bottom.value=a;else top.value=a;await refresh()}catch(e){hint(e)}finally{busy.value=false}}
 function valid(){
  if(!Number.isFinite(Number(profile.height))||Number(profile.height)<120||Number(profile.height)>220)throw new Error('身高请输入 120～220 cm')
  if(!Number.isFinite(Number(profile.weight))||Number(profile.weight)<30||Number(profile.weight)>200)throw new Error('体重请输入 30～200 kg')
  if(!Number.isInteger(Number(profile.age))||Number(profile.age)<18||Number(profile.age)>80)throw new Error('年龄请输入 18～80 岁')
 }
 function running(){return !!current.value&&!['succeeded','failed','canceled'].includes(current.value.status)}
 const normalized=()=>({...profile,height:Number(profile.height),weight:Number(profile.weight),age:Number(profile.age)})
 async function generatePortrait(){if(!ensureLogin())return;if(busy.value||running())return;busy.value=true;try{valid();const payload={profile:normalized()};const signature=JSON.stringify(payload);let pending=uni.getStorageSync('pendingPortrait');if(!pending||pending.signature!==signature){pending={signature,id:requestId()};uni.setStorageSync('pendingPortrait',pending)};active(await request<Task>('/api/portraits','POST',{...payload,request_id:pending.id}));uni.removeStorageSync('pendingPortrait');await refresh()}catch(e:any){if([400,409,422].includes(e.status))uni.removeStorageSync('pendingPortrait');hint(e)}finally{busy.value=false}}
 async function generate(){if(!ensureLogin())return;if(busy.value||running())return;busy.value=true;try{valid();if(!person.value)throw new Error('请上传或生成一张人像');if(!top.value&&!bottom.value)throw new Error('请选择至少一件服饰')
 const payload={person:person.value.id,top:top.value?.id||null,bottom:category.value==='dress'?null:bottom.value?.id||null,dress:category.value==='dress',preserve:preserve.value,profile:normalized()};const signature=JSON.stringify(payload);let pending=uni.getStorageSync('pendingTryon');if(!pending||pending.signature!==signature){pending={signature,id:requestId()};uni.setStorageSync('pendingTryon',pending)}
 active(await request<Task>('/api/tryon','POST',{...payload,request_id:pending.id}));uni.removeStorageSync('pendingTryon');await loadOriginal();go('preview');await refresh()}catch(e:any){if([400,409,422].includes(e.status))uni.removeStorageSync('pendingTryon');hint(e)}finally{busy.value=false}}
 function switchCategory(v:string){if(v===category.value)return;category.value=v;top.value=undefined;if(v==='dress')bottom.value=undefined}
 function preview(a?:Asset){if(a)uni.previewImage({urls:[imageUrl(a)]})}
 function save(a?:Asset){if(!a)return
  // #ifdef H5
  const link=document.createElement('a');link.href=imageUrl(a);link.target='_blank';link.rel='noopener';link.click();return
  // #endif
  // #ifndef H5
  uni.downloadFile({url:imageUrl(a),success:r=>{if(r.statusCode!==200){hint(new Error('下载失败'));return}uni.saveImageToPhotosAlbum({filePath:r.tempFilePath,success:()=>uni.showToast({title:'已保存'}),fail:()=>hint(new Error('保存失败，请允许相册权限'))})},fail:()=>hint(new Error('下载失败'))})
  // #endif
 }
 async function removeRecord(t:Task){const confirmed=await new Promise<boolean>(resolve=>uni.showModal({title:'删除这条记录？',content:'删除后无法恢复记录；图片素材仍保留在衣橱。',success:r=>resolve(r.confirm),fail:()=>resolve(false)}));if(!confirmed)return;try{await request('/api/tasks/'+t.id,'DELETE');if(current.value?.id===t.id){current.value=undefined;uni.removeStorageSync('activeTask')};await refresh()}catch(e){hint(e)}}
 async function removeAsset(a:Asset){const confirmed=await new Promise<boolean>(resolve=>uni.showModal({title:'删除这张图片？',content:'图片文件会永久删除。被生成记录引用的图片需要先删除相关记录。',success:r=>resolve(r.confirm),fail:()=>resolve(false)}));if(!confirmed)return;try{await request('/api/assets/'+a.id,'DELETE');if(person.value?.id===a.id)person.value=undefined;if(top.value?.id===a.id)top.value=undefined;if(bottom.value?.id===a.id)bottom.value=undefined;await refresh();await searchWardrobe()}catch(e){hint(e)}}
 function pickAsset(a:Asset){if(a.kind==='person'){selectPerson(a);uni.switchTab({url:'/pages/index/index'})}else{if(a.kind==='bottom'){if(category.value==='dress'){category.value='top';top.value=undefined}bottom.value=a}else{top.value=a;category.value=a.kind==='dress'?'dress':'top';if(category.value==='dress')bottom.value=undefined}go('garments')}}
 function openTask(t:Task){active(t);if(t.kind==='tryon'){void loadOriginal();go('preview')}else if(t.result){selectPerson(t.result);uni.switchTab({url:'/pages/index/index'})}else{uni.switchTab({url:'/pages/index/index'})}}
 async function reuse(){if(!current.value||current.value.kind!=='tryon')return;try{const s=current.value.snapshot;const [p,t,b]=await Promise.all([snapshotAsset(s.person),snapshotAsset(s.top),snapshotAsset(s.bottom)]);person.value=p;top.value=t;bottom.value=b;category.value=s.dress?'dress':'top';preserve.value=s.preserve;Object.assign(profile,s.profile);go('garments')}catch(e){hint(e)}}

 return {search,favoritesOnly,wardrobe,wardrobeMore,searchWardrobe,toggleFavorite,renameAsset,cancelCurrent,removeRecord,removeAsset,moreAssets,assetFilter,loadMoreAssets,networkError,loading,hasMore,moreHistory,start,stop,go,next,edit,original,loadOriginal,reuse,user,source,person,top,bottom,category,busy,preserve,current,history,library,config,profile,genders,shapes,labels,refresh,choose,generatePortrait,generate,switchCategory,preview,save,pickAsset,openTask,running,imageUrl}
}

let shared:ReturnType<typeof createStudio>|undefined
export function useStudio(){if(!shared)shared=createStudio();const studio=shared;onShow(studio.start);onHide(studio.stop);onUnload(studio.stop);return studio}
