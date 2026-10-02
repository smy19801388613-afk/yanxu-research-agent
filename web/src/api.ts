export async function api(path:string,options:any={}){
  const r=await fetch('/api'+path,{...options,headers:options.body instanceof FormData?options.headers:{'Content-Type':'application/json',...options.headers}});
  if(!r.ok){const e=await r.json().catch(()=>({detail:'请求失败'}));throw new Error(typeof e.detail==='string'?e.detail:e.detail?.map((v:any)=>v.msg).join('；')||'请求失败')}
  return r.json();
}
export const post=(path:string,body:any={})=>api(path,{method:'POST',body:JSON.stringify(body)});
export const decimal=(value:any)=>value==null?'—':Number(value).toLocaleString('zh-CN',{maximumFractionDigits:2});
