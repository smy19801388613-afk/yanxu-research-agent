import {useEffect,useId,useRef,useState} from 'react';
import {Search,RefreshCw,Check,LoaderCircle} from 'lucide-react';
import {api,post} from './api';

export default function CompanySearch({value,onChange,disabled=false}:any){
  const [query,setQuery]=useState(value||''),[data,setData]=useState<any>(null),[open,setOpen]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(''),[index,setIndex]=useState(0);
  const sequence=useRef(0),box=useRef<HTMLDivElement>(null),id=useId();
  useEffect(()=>{if(value)setQuery(value)},[value]);
  useEffect(()=>{
    const controller=new AbortController(),n=++sequence.current;
    const timer=setTimeout(()=>{setBusy(true);api('/securities?q='+encodeURIComponent(query),{signal:controller.signal})
      .then(d=>{if(n===sequence.current){setData(d);setError('');setIndex(0)}})
      .catch(e=>{if(e.name!=='AbortError'&&n===sequence.current)setError(e.message)})
      .finally(()=>{if(n===sequence.current)setBusy(false)})},250);
    return()=>{clearTimeout(timer);controller.abort()}
  },[query]);
  useEffect(()=>{const close=(e:MouseEvent)=>{if(!box.current?.contains(e.target as Node))setOpen(false)};document.addEventListener('mousedown',close);return()=>document.removeEventListener('mousedown',close)},[]);
  function choose(row:any){onChange(row.ts_code,row);setQuery(row.name+' · '+row.ts_code);setOpen(false)}
  async function refresh(){setBusy(true);try{const d=await post('/securities/refresh');setData({...d,items:d.items});setQuery('');setOpen(true);setError('')}catch(e:any){setError(e.message)}finally{setBusy(false)}}
  const rows=data?.items||[];
  return <div className="company-search" ref={box}>
    <label htmlFor={id}>公司名称 / 拼音缩写 / 证券代码</label>
    <div className="search-input-wrap"><Search size={16}/><input id={id} role="combobox" aria-expanded={open} aria-controls={id+'-list'} aria-activedescendant={open&&rows[index]?id+'-'+index:undefined} autoComplete="off" disabled={disabled} placeholder="例如：美的、MDJT、000333" value={query} onFocus={()=>setOpen(true)} onChange={e=>{setQuery(e.target.value);setOpen(true);const v=e.target.value.trim().toUpperCase();onChange(/^\d{6}\.(SH|SZ|BJ)$/.test(v)?v:'')}} onKeyDown={e=>{if(e.key==='ArrowDown'){e.preventDefault();setOpen(true);setIndex(i=>Math.min(i+1,rows.length-1))}if(e.key==='ArrowUp'){e.preventDefault();setIndex(i=>Math.max(0,i-1))}if(e.key==='Enter'&&open&&rows[index]){e.preventDefault();choose(rows[index])}if(e.key==='Escape'){e.stopPropagation();setOpen(false)}}}/>{busy?<LoaderCircle size={16} className="spin"/>:<button type="button" className="icon-button" aria-label="刷新证券目录" disabled={disabled} onClick={refresh}><RefreshCw size={14}/></button>}</div>
    {value&&<div className="selected-security"><Check size={12}/> 已选 {value}</div>}
    {open&&!disabled&&<div className="search-results" id={id+'-list'} role="listbox">
      {rows.map((r:any,i:number)=><button type="button" id={id+'-'+i} role="option" aria-selected={i===index} className={i===index?'focused':''} key={r.ts_code} onMouseDown={e=>e.preventDefault()} onClick={()=>choose(r)}><span><strong>{r.name}</strong><small>{r.industry||r.fullname||r.cnspell}</small></span><code>{r.ts_code}</code></button>)}
      {!rows.length&&<p>{busy?'正在查询证券目录…':'未找到匹配项，可填写完整代码，如 000333.SZ'}</p>}
      <div className="directory-note">{data?.source} {data?.total?('· '+data.total+' 家'):''}<br/>{data?.updated_at?'更新于 '+new Date(data.updated_at).toLocaleString('zh-CN'):''}{data?.stale?' · 缓存待刷新':''}{data?.note&&<p>{data.note}</p>}{error&&<p className="form-error">{error}</p>}</div>
    </div>}
  </div>
}
