"""Apply the small integration changes to the existing compact App component once."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
path=root/'web/src/App.tsx'
text=path.read_text(encoding='utf-8')
if "import HistoryTrash" not in text:
    changes=[
        ("Command,MessageSquare}","Command,MessageSquare,Trash2}"),
        ("import AgentChat from './AgentChat';","import AgentChat from './AgentChat';\nimport HistoryTrash from './HistoryTrash';"),
        ("settings:'连接设置'}","settings:'连接设置',trash:'回收站'}"),
        ("  async function selectRun(id:string)","""  async function removeRun(id:string){setError('');try{await api('/runs/'+id,{method:'DELETE'});const rows=await api('/runs');setRuns(rows);if(run?.id===id){setRun(null);localStorage.removeItem('research-run');if(rows.length)await selectRun(rows[0].id);else setTab('trash')}setNotice('研究及关联对话已移入回收站，可恢复；PDF 资料保留。')}catch(e:any){setError(e.message)}}
  async function attachExisting(d:any){setError('');try{if(!run)throw new Error('请先选择一份匹配的公司研究');const rows=await api('/conversations?run_id='+run.id);const saved=localStorage.getItem('research-conversation:'+run.id);const c=rows.find((r:any)=>r.id===saved)||rows[0]||await post('/conversations',{run_id:run.id});await post('/conversations/'+c.id+'/documents/'+d.id);localStorage.setItem('research-conversation:'+run.id,c.id);await selectRun(run.id);setTab('chat');setNotice('材料已接入当前对话，可以直接提问。')}catch(e:any){setError(e.message)}}
  useEffect(()=>{if(tab==='library')api('/documents').then(setDocs).catch(e=>setError(e.message))},[tab]);
  useEffect(()=>{if(run)setUploadMeta({ticker:run.request.ticker,year:run.request.year,announced_date:''})},[run?.id]);
  async function selectRun(id:string)"""),
        ("[Settings2,'settings']].map","[Settings2,'settings'],[Trash2,'trash']].map"),
        ("!['library','settings','chat'].includes(tab)","!['library','settings','chat','trash'].includes(tab)"),
        ('<span>V 0.2</span>','<span>V 0.2.1</span>'),
        ('LOCAL · v0.2</span>','LOCAL · v0.2.1</span>'),
        ('<button className="primary" onClick={()=>setShowExport(true)}', '<button className="secondary" aria-label="删除当前研究" disabled={busy} onClick={()=>removeRun(run.id)}><Trash2 size={15}/>删除研究</button><button className="primary" onClick={()=>setShowExport(true)}'),
        ('<td><button className="text-link" onClick={()=>selectRun(r.id)}>查看<ArrowRight size={13}/></button></td>', '<td><div className="button-row"><button className="text-link" onClick={()=>selectRun(r.id)}>查看<ArrowRight size={13}/></button><button className="text-link" aria-label={"删除研究 "+r.company+" "+r.id.slice(0,6)} disabled={["queued","running"].includes(r.state)} onClick={()=>removeRun(r.id)}><Trash2 size={14}/>删除</button></div></td>'),
        ('支持文本型年度报告摘要的核心财务表。其他版式与扫描件可能需要人工核验。最多 20 MB / 320 页。','支持文本 PDF 全文查阅，最多 100 MB / 800 页。扫描页可用本机 OCR 查阅；财务数值需核对原图。上传后可接入当前研究对话。'),
        ("{d.kind==='official_sample'?'官方样例':'本地材料'}","{d.kind==='official_sample'?'官方样例':d.kind==='public_report'?'公开年报':'本地材料'}"),
        ('公告日期 {d.announced_date}</small>','公告日期 {d.announced_date||\'未确认\'} · {d.page_count?d.page_count+\' 页\':\'可查阅\'}</small>'),
        ('>用于研究<ArrowRight size={13}/></button></div></section>)}</div></div>}', '>用于新研究<ArrowRight size={13}/></button>{run&&d.ticker===run.request.ticker&&d.year===run.request.year&&<button className="text-link" disabled={busy} onClick={()=>attachExisting(d)}>接入当前对话<ArrowRight size={13}/></button>}</div></section>)}</div></div>}'),
        ("        {tab==='settings'&&", "        {tab==='trash'&&<HistoryTrash onRestored={refreshRuns}/>}\n        {tab==='settings'&&"),
    ]
    for old,new in changes:
        if old not in text: raise RuntimeError('Missing integration marker: '+old[:100])
        text=text.replace(old,new)
    path.write_text(text,encoding='utf-8')
path=root/'web/src/AgentChat.tsx'
text=path.read_text(encoding='utf-8')
if '<DocumentLinks documents={attached}/>' not in text:
    text=text.replace('<div className="companion-note">','<DocumentLinks documents={attached}/><div className="companion-note">')
    path.write_text(text,encoding='utf-8')
print('UI integration complete')
