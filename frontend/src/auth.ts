import { ref } from 'vue'
import { request, applyLogin, clearSession, type User, type LoginResult } from './api'
export const user=ref<User|undefined>(uni.getStorageSync('sessionUser')||undefined)
export const authConfig=ref<any>()
export const authBusy=ref(false)
uni.$on('session-cleared',()=>{user.value=undefined})
uni.$on('session-ready',(account:User)=>{user.value=account})
uni.$on('session-renewed',(account:User)=>{user.value={...user.value,...account}})
const toast=(e:any)=>uni.showToast({title:e.message||String(e),icon:'none',duration:3500})
export function ensureLogin(){if(uni.getStorageSync('accessToken'))return true;openLogin();return false}
export function openLogin(returnTo?:string){const pages=getCurrentPages();const current=pages[pages.length-1]?.route||'pages/index/index';if(current==='pages/login/index')return;uni.setStorageSync('loginReturn',returnTo||'/'+current);uni.navigateTo({url:'/pages/login/index'})}
export async function loadAuthConfig(){try{authConfig.value=await request('/api/auth/config')}catch(e){toast(e)}}
export async function loadMe(){if(!uni.getStorageSync('accessToken'))return;try{user.value=await request<User>('/api/me');uni.setStorageSync('sessionUser',user.value)}catch(e){toast(e)}}
export function afterLogin(){const allowed=['/pages/index/index','/pages/mine/index','/pages/garments/index','/pages/wardrobe/index','/pages/history/index','/pages/profile/index','/pages/account/index'];const saved=uni.getStorageSync('loginReturn');uni.removeStorageSync('loginReturn');const target=allowed.includes(saved)?saved:'/pages/mine/index';if(['/pages/index/index','/pages/mine/index'].includes(target))uni.switchTab({url:target});else{const pages=getCurrentPages();if('/'+pages[pages.length-2]?.route===target)uni.navigateBack();else uni.redirectTo({url:target})}}
export async function devLogin(accepted:boolean){if(!accepted){toast(new Error('请先阅读并同意用户协议和隐私说明'));return}if(authBusy.value)return;authBusy.value=true;try{applyLogin(await request<LoginResult>('/api/auth/dev-login','POST',{accepted_version:authConfig.value?.consent_version}));afterLogin()}catch(e){toast(e)}finally{authBusy.value=false}}
export async function wechatLogin(accepted:boolean){if(!accepted){toast(new Error('请先阅读并同意用户协议和隐私说明'));return}if(authBusy.value)return;authBusy.value=true;try{
 const version=authConfig.value?.consent_version
 // #ifdef MP-WEIXIN
 if(!authConfig.value?.wechat.mini)throw new Error('微信登录暂未开通')
 const miniResult:any=await new Promise((resolve,reject)=>uni.login({provider:'weixin',success:resolve,fail:()=>reject(new Error('微信授权未完成，请重试'))}))
 applyLogin(await request<LoginResult>('/api/auth/wechat','POST',{channel:'mini',code:miniResult.code,accepted_version:version}));afterLogin()
 // #endif
 // #ifdef APP-PLUS
 if(!authConfig.value?.wechat.app)throw new Error('微信登录暂未开通')
 const appResult:any=await new Promise((resolve,reject)=>uni.login({provider:'weixin',onlyAuthorize:true,success:resolve,fail:()=>reject(new Error('微信授权未完成，请检查微信安装状态'))}))
 applyLogin(await request<LoginResult>('/api/auth/wechat','POST',{channel:'app',code:appResult.code,accepted_version:version}));afterLogin()
 // #endif
 // #ifdef H5
 const channel=/MicroMessenger/i.test(navigator.userAgent)?'h5':'web'
 if(!authConfig.value?.wechat[channel])throw new Error('微信登录暂未开通')
 const bytes=crypto.getRandomValues(new Uint8Array(32));const verifier=Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('')
 const hash=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(verifier));const challenge=Array.from(new Uint8Array(hash),b=>b.toString(16).padStart(2,'0')).join('')
 const webStart=await request<{url:string;state:string}>('/api/auth/wechat/start','POST',{channel,challenge,accepted_version:version})
 sessionStorage.setItem('wechatOAuth',JSON.stringify({verifier,state:webStart.state,channel,version}));window.location.assign(webStart.url)
 // #endif
 }catch(e){toast(e)}finally{authBusy.value=false}}
export async function handleOAuthCallback(){
 // #ifdef H5
 const params=new URLSearchParams(window.location.search);if(!params.has('state'))return
 const saved=sessionStorage.getItem('wechatOAuth');sessionStorage.removeItem('wechatOAuth');window.history.replaceState({},'',window.location.pathname+window.location.hash)
 if(!saved){toast(new Error('授权状态已失效，请重新登录'));return}
 try{const state=JSON.parse(saved);if(params.get('state')!==state.state||!params.get('code'))throw new Error('微信授权未完成，请重新登录');applyLogin(await request<LoginResult>('/api/auth/wechat','POST',{channel:state.channel,code:params.get('code'),state:state.state,verifier:state.verifier,accepted_version:state.version}));afterLogin()}catch(e){toast(e)}
 // #endif
}
export async function logout(all=false){const yes=await new Promise<boolean>(resolve=>uni.showModal({title:all?'退出所有设备？':'退出登录？',content:'已提交的生成任务仍会继续。',success:r=>resolve(r.confirm)}));if(!yes)return;try{await request('/api/auth/'+(all?'logout-all':'logout'),'POST');clearSession();uni.switchTab({url:'/pages/mine/index'})}catch(e){toast(e)}}
export async function deleteAccount(){const yes=await new Promise<boolean>(resolve=>uni.showModal({title:'确认注销账号？',content:'你的账号、照片、生成记录和反馈将被删除，无法恢复。进行中的任务需先结束或取消。',confirmText:'确认注销',confirmColor:'#d65b66',success:r=>resolve(r.confirm)}));if(!yes)return;try{await request('/api/me','DELETE');clearSession();uni.showToast({title:'注销请求已受理',icon:'none'});uni.switchTab({url:'/pages/mine/index'})}catch(e){toast(e)}}
