"""One-time, guarded migration of the existing v0.1 view to v0.2 components."""
from pathlib import Path

p=Path(__file__).resolve().parents[1]/"web/src/App.tsx"
s=p.read_text(encoding="utf-8")
if "import AgentChat" in s: raise SystemExit("Already upgraded")
s=s.replace("type Run=any;","import AgentChat from './AgentChat';\nimport CompanySearch from './CompanySearch';\nimport ConnectionSettings from './ConnectionSettings';\nimport ValuationLab from './ValuationLab';\n\ntype Run=any;")
s=s.replace("AlertCircle,Command}","AlertCircle,Command,MessageSquare}")
s=s.replace("{overview:'公司研究',model:'情景建模'","{chat:'研究对话',overview:'公司研究',model:'估值建模'")
s=s.replace("useState('overview')","useState('chat')",1)
s=s.replace("  const [selected,setSelected]","  const [chatPrompt,setChatPrompt]=useState('');\n  const [selected,setSelected]",1)
s=s.replace("mode:'live',use_model:true,document_id:''","mode:'live',use_model:true,document_id:'',data_source:'default'")
s=s.replace("<span>V 0.1</span>","<span>V 0.2</span>").replace("LOCAL · v0.1","LOCAL · v0.2")
s=s.replace("className=\"brand\" onClick={()=>setTab('overview')}","className=\"brand\" onClick={()=>setTab('chat')}")
s=s.replace("[[BookOpen,'overview']","[[MessageSquare,'chat'],[BookOpen,'overview']",1)
s=s.replace("['library','settings'].includes(tab)","['library','settings','chat'].includes(tab)")
s=s.replace("Tushare {config.tushare_configured?'已配置':'未配置'}","{config.model||'配置连接'}")
s=s.replace("config.tushare_configured?'green-dot':'gray-dot'","config.model_configured?'green-dot':'gray-dot'")
s=s.replace("{s.kind==='document'?'原始披露':'Tushare'}","{s.kind==='document'?'原始披露':s.id.startsWith('eastmoney')?'公开财务':'Tushare'}")
s=s.replace('  async function start(data=form)',"  function discuss(text:string){setChatPrompt(text);setTab('chat')}\n  async function updated(id:string){await selectRun(id);await refreshRuns()}\n  async function start(data=form)")
lines=s.splitlines()
for i,line in enumerate(lines):
    if "{tab==='model'&&run&&" in line:
        lines[i]="        {tab==='model'&&run&&<ValuationLab key={run.id} run={run} onUpdated={updated} onDiscuss={discuss}/>}"
    elif "{tab==='settings'&&" in line:
        lines[i]="        {tab==='settings'&&<ConnectionSettings config={config} onChange={setConfig}/>}"
    elif "{showNew&&<Modal" in line:
        lines[i]='''    {showNew&&<Modal title="开始一份新研究" onClose={()=>setShowNew(false)}><form onSubmit={e=>{e.preventDefault();start()}}>
      <div className="mode-options"><button type="button" className={form.mode==='live'?'selected':''} onClick={()=>setForm({...form,mode:'live'})}><Sparkles size={20}/><strong>实时研究</strong><span>选择数据源 · 模型分析</span></button><button type="button" className={form.mode==='sample'?'selected':''} onClick={()=>setForm({...form,mode:'sample',ticker:'000333.SZ',year:2025,document_id:''})}><BookOpen size={20}/><strong>样例回放</strong><span>美的 2025 · 已保存快照</span></button></div>
      <CompanySearch value={form.ticker} disabled={form.mode==='sample'} onChange={(ticker:string)=>setForm((f:any)=>({...f,ticker,document_id:''}))}/>
      <div className="form-row"><label>报告年度<input required type="number" min="2000" max={new Date().getFullYear()} value={form.year} disabled={form.mode==='sample'} onChange={e=>setForm({...form,year:Number(e.target.value),document_id:''})}/></label><label>研究截止日<input required type="date" max={config.today} value={form.as_of} onChange={e=>setForm({...form,as_of:e.target.value})}/></label></div>
      {form.mode==='live'&&<label>本次数据源<select value={form.data_source||'default'} onChange={e=>setForm({...form,data_source:e.target.value})}><option value="default">使用默认 · {config.data_sources?.find((s:any)=>s.id===config.data_source)?.name}</option>{config.data_sources?.map((s:any)=><option key={s.id} value={s.id}>{s.name}</option>)}</select></label>}
      <label>研究问题<textarea required minLength={4} maxLength={1500} rows={3} value={form.question} onChange={e=>setForm({...form,question:e.target.value})}/></label><label>参考材料<select value={form.document_id||''} onChange={e=>setForm({...form,document_id:e.target.value})}><option value="">自动匹配内置材料 / 仅结构化数据</option>{docs.filter(d=>d.ticker===form.ticker&&d.year===Number(form.year)).map(d=><option key={d.id} value={d.id}>{d.title}</option>)}</select></label>{form.mode==='live'&&<label className="checkbox-label"><input type="checkbox" checked={form.use_model} onChange={e=>setForm({...form,use_model:e.target.checked})}/>调用模型提出研究追问并生成草稿</label>}<div className="modal-note">{form.mode==='sample'?'样例使用 2026-09-28 保存的数据，不调用实时接口或模型。':'完成财务底稿后，可以在研究对话中继续讨论、估值或修订报告。'}</div>{error&&<p className="form-error">{error}</p>}<button className="primary full" disabled={creating||!form.ticker} type="submit">{creating?<LoaderCircle size={17} className="spin"/>:<ArrowRight size={17}/>}开始研究</button></form></Modal>}'''
s="\n".join(lines)+"\n"
anchor="        {tab==='overview'&&run&&"
s=s.replace(anchor,"        {tab==='chat'&&<AgentChat key={run?.id||'free'} run={run} config={config} onRunUpdated={updated} onOpen={setTab} onNewResearch={()=>setShowNew(true)} prompt={chatPrompt}/>}\n"+anchor,1)
anchor="        {tab==='history'&&run&&"
history='''        {tab==='history'&&run&&<div className="content-page"><section className="panel memo-revisions"><div className="panel-heading"><h2>报告修订记录</h2><Badge>当前第 {run.report_revision||1} 版</Badge></div><p className="pad small-muted">在研究对话中提出“更新报告”，新稿会替换当前报告，旧稿保存在这里。</p>{[...(run.memo_revisions||[])].reverse().map((v:any)=><details key={v.revision}><summary>第 {v.revision} 版 → 第 {v.revision+1} 版 · {v.change_note} <small>{when(v.replaced_at)}</small></summary><h3>{v.memo?.title}</h3><p>{v.memo?.summary}</p>{v.memo?.theses.map((t:any,i:number)=><div key={i}><strong>{t.title}</strong><p>{t.body}</p></div>)}</details>)}</section></div>}
'''
s=s.replace(anchor,history+anchor,1)
s=s.replace("研究判断</h2>","研究判断 · 第 {run.report_revision||1} 版</h2>")
# Remove the retired PE-only component state and action.
lines=[line for line in s.splitlines() if not line.startswith("  const [inputs,setInputs]") and not line.startswith("  async function calculate()")]
s="\n".join(lines)+"\n"
start=s.index(";setScenario(");end=s.index(";setComparison(null)",start)
s=s[:start]+s[end:]
p.write_text(s,encoding="utf-8")
