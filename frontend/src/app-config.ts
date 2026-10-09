// Service configuration belongs to the developer, never the end user.
export function apiBase(){
 const configured=import.meta.env.VITE_API_BASE_URL as string | undefined
 if(configured)return configured.replace(/\/$/,'')
 let base='http://127.0.0.1:8000'
 // #ifdef H5
 base=import.meta.env.PROD?window.location.origin+'/api-backend':window.location.protocol+'//'+window.location.hostname+':8000'
 // #endif
 return base
}
export const APP_VERSION='1.0.0'
