<script setup lang="ts">
import { onLaunch } from '@dcloudio/uni-app'
import { handleOAuthCallback } from './auth'
onLaunch(()=>{uni.removeStorageSync('apiBase');uni.removeStorageSync('apiToken');void handleOAuthCallback()})
</script>
<style>
@import "./styles/app.css";

page { background:#f5f9ff;color:#253b55;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:14px }
button::after { border:0 } button { font-size:14px } view,text,button,input { box-sizing:border-box }
</style>
