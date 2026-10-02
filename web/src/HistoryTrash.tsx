import {useEffect,useState} from 'react';
import {RotateCcw,Trash2} from 'lucide-react';
import {api,post} from './api';
export default function HistoryTrash({onRestored}:any){
  const [rows,setRows]=useState<any[]>([]),[error,setError]=useState(''),[busy,setBusy]=useState('');
  const refresh=()=>api('/trash').then(setRows);
  useEffect(()=>{refresh().catch(e=>setError(e.message))},[]);
  async function restore(r:any){setBusy(r.id);setError('');try{await post('/trash/'+r.kind+'/'+r.id+'/restore');await refresh();await onRestored()}catch(e:any){setError(e.message)}finally{setBusy('')}}
  return <div className="content-page"><div className="section-heading"><div><span className="eyebrow">RECYCLE BIN</span><h1><Trash2 size={24}/>回收站</h1><p className="small-muted">删除的研究与对话可在这里恢复。恢复研究会同时恢复随它移入的对话；资料库中的 PDF 始终保留。</p></div></div>{error&&<p role="alert" className="form-error">{error}</p>}<section className="panel history-table"><table><thead><tr><th>名称</th><th>类型</th><th>删除时间</th><th/></tr></thead><tbody>{rows.map(r=><tr key={r.kind+r.id}><td>{r.title}</td><td>{r.kind==='run'?'公司研究':'研究对话'}</td><td>{new Date(r.deleted_at).toLocaleString('zh-CN')}</td><td><button className="text-link" disabled={!!busy} onClick={()=>restore(r)}><RotateCcw size={14}/>恢复</button></td></tr>)}</tbody></table>{!rows.length&&<p className="pad small-muted">回收站为空。</p>}</section></div>
}
