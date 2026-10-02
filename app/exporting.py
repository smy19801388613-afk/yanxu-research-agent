import json
import re
from html import escape
from decimal import Decimal
from .finance import METRICS,number

def memo_references(memo,ids):
    catalog={s['id']:s for s in memo.get('sources',[])}
    return [catalog[i] for i in ids if i in catalog]

def export_url(url):
    # Downloaded reports must still resolve local evidence outside the app URL.
    return 'http://127.0.0.1:8920'+url if url.startswith('/api/documents/') else url

def reference_markdown(memo,ids):
    return '；'.join('['+s['title']+']('+export_url(s['url'])+')' if s.get('url') else s['title'] for s in memo_references(memo,ids))

def reference_html(memo,ids):
    return ' · '.join('<a href="'+escape(export_url(s['url']),quote=True)+'">'+escape(s['title'])+'</a>' if s.get('url') else escape(s['title']) for s in memo_references(memo,ids))

def prose_html(value):
    # Escape before the tiny Markdown presentation pass: never execute model HTML.
    return ''.join('<p>'+re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',escape(p)).replace('\n','<br>')+'</p>' for p in str(value).split('\n\n') if p.strip())

def markdown(run):
    req=run["request"];memo=run.get("memo") or {}
    lines=[f"# {memo.get('title') or run['company']+' · '+str(req['year'])+' 年财务研究'}",f"研究问题：{req['question']}",
        f"截止日：{req['as_of']} | 模式：{'样例回放' if req['mode']=='sample' else '实时研究'} | 状态：{run['state']}",
        "\n## 核心财务事实（人民币亿元）","| 指标 | 本期 | 上期 | 同比 |","|---|---:|---:|---:|"]
    for metric,meta in METRICS.items():
        vals=[]
        for year in (req["year"],req["year"]-1):
            f=next((f for f in run["facts"] if f["metric"]==metric and f["year"]==year),None)
            vals.append(f"{number(f['value'])/Decimal(100000000):,.2f}" if f else "缺失")
        c=next((c for c in run["calculations"] if c["metric"]==metric),None)
        rate=f"{number(c['value']):+.2f}%" if c and c["value"] is not None else "不适用/缺失"
        lines.append(f"| {meta['label']} | {vals[0]} | {vals[1]} | {rate} |")
    lines += ["\n同比公式：(本期 / 上期 - 1) × 100%；零或负基期不套用该公式。",
        "\n## 研究判断（待复核）",memo.get("summary","研究尚未完成。")]
    if memo.get('stance'): lines += ['研究立场：'+memo['stance']]
    for t in memo.get("theses",[]):
        lines += ["\n### "+t["title"],t["body"],"依据："+(reference_markdown(memo,t.get('evidence_ids',[])) or ", ".join(t["fact_ids"])),
            "反方证据/替代解释："+t["counter_evidence"],"修订条件："+t["invalidate_if"]]
    for s in memo.get('sections',[]):
        lines += ['\n## '+s['title'],s['body'],'依据：'+(reference_markdown(memo,s.get('evidence_ids',[])) or '证据待补充')]
    if memo.get('questions'): lines += ['\n## 下一步核实清单']+['- '+q for q in memo['questions']]
    if memo.get('sources'):
        lines += ['\n## 研究来源目录']
        for s in memo['sources']:
            lines += ['- '+reference_markdown(memo,[s['id']])+' | '+s.get('read_status',s.get('status',s['kind']))+' | 披露日期：'+str(s.get('published_at') or '待核实')]
    if memo.get('review'):
        lines += ['\n## 反方审阅记录',memo['review']['semantic_status']]+['- '+str(v) for v in memo['review'].get('issues',[])]
    lines += ["\n## 待核实与限制"]+["- "+g["message"] for g in run["gaps"]]+["- "+s for s in memo.get("limitations",[])]
    lines += ["\n## 数据与计算证据"]
    for e in run["evidence"]:
        lines += [f"\n### {e['id']} · {e['title']}",e["locator"],e.get("source_url") or "本地上传文件",e["quote"]]
    lines += ["\n## 计算记录"]+[json.dumps(c,ensure_ascii=False) for c in run["calculations"]]
    if run.get("scenario_history"):
        lines += ["\n## 用户情景（探索假设）"]+[json.dumps(s,ensure_ascii=False) for s in run["scenario_history"]]
    if run.get("valuation_history"):
        lines += ["\n## 多方法估值与假设"]+[json.dumps(v,ensure_ascii=False,indent=2) for v in run["valuation_history"]]
    if run.get("memo_revisions"):
        lines += [f"\n## 报告修订记录（当前第 {run.get('report_revision',1)} 版）"]+[json.dumps(v,ensure_ascii=False,indent=2) for v in run["memo_revisions"]]
    if run.get("attached_documents"):
        lines += ["\n## 对话补充材料", "以下材料已接入全文查阅，未自动覆盖已核验财务事实。"]+[json.dumps(d,ensure_ascii=False) for d in run["attached_documents"]]
    lines += ["\n## 运行记录",f"Run ID: {run['id']} | 版本: {run['version']}"]+[f"- {e['time']} {e['label']}：{e['detail']}" for e in run["events"]]
    return re.sub(r"(\|[^\n]*\|)\n\n(?=\|)",r"\1\n","\n\n".join(lines))

def printable(run):
    req=run["request"];memo=run.get("memo") or {}
    def e(value): return escape(str(value))
    def amount(fact):
        return f"{number(fact['value'])/Decimal(100000000):,.2f}" if fact else "缺失"
    rows=[]
    for metric,meta in METRICS.items():
        current=next((f for f in run["facts"] if f["metric"]==metric and f["year"]==req["year"]),None)
        previous=next((f for f in run["facts"] if f["metric"]==metric and f["year"]==req["year"]-1),None)
        calc=next((c for c in run["calculations"] if c["metric"]==metric),None)
        rate=f"{number(calc['value']):+.2f}%" if calc and calc["value"] is not None else "不适用/缺失"
        state={"verified":"双源一致","document_only":"披露文件","api_only":"接口来源","conflict":"来源冲突"}.get(current["status"],"") if current else "缺失"
        rows.append(f"<tr><th>{e(meta['label'])}</th><td>{amount(current)}</td><td>{amount(previous)}</td><td>{rate}</td><td>{state}</td></tr>")
    sections=[]
    for t in memo.get("theses",[]):
        sections.append("<section class='thesis'><h3>"+e(t["title"])+"</h3>"+prose_html(t["body"])+"<p class='muted'>依据："+(reference_html(memo,t.get('evidence_ids',[])) or e(" / ".join(t["fact_ids"])))+"</p><div class='counter'><b>反方 / 替代解释</b><p>"+e(t["counter_evidence"])+"</p><b>何时修订判断</b><p>"+e(t["invalidate_if"])+"</p></div></section>")
    for s in memo.get('sections',[]):
        sections.append('<section><h2>'+e(s['title'])+'</h2>'+prose_html(s['body'])+'<p class="muted">依据：'+(reference_html(memo,s.get('evidence_ids',[])) or '证据待补充')+'</p></section>')
    if memo.get('sources'):
        sections.append('<h2>研究来源目录</h2>'+''.join('<article><h3>'+reference_html(memo,[s['id']])+'</h3><p class="muted">'+e(s.get('read_status',s.get('status',s['kind'])))+' · 披露日期 '+e(s.get('published_at') or '待核实')+'</p><details><summary>来源摘录</summary>'+prose_html(s.get('text',''))+'</details></article>' for s in memo['sources']))
    if memo.get('review'):
        sections.append('<details><summary>反方审阅记录</summary><p>'+e(memo['review']['semantic_status'])+'</p><ul>'+''.join('<li>'+e(v)+'</li>' for v in memo['review'].get('issues',[]))+'</ul></details>')
    limitations=[g["message"] for g in run["gaps"]]+memo.get("limitations",[])
    sources=[]
    for source in run["evidence"]:
        link=f"<a href='{e(source['source_url'])}'>原始来源</a>" if source.get("source_url") else "本地上传"
        sources.append(f"<article><h3>{e(source['title'])}</h3><p class='muted'>{e(source['id'])} · {e(source['locator'])} · {link}</p><pre>{e(source['quote'])}</pre></article>")
    calc_html="".join("<pre>"+e(json.dumps(c,ensure_ascii=False,indent=2))+"</pre>" for c in run["calculations"])
    scenario_html=("<h2>用户探索情景</h2>"+"".join("<pre>"+e(json.dumps(s,ensure_ascii=False,indent=2))+"</pre>" for s in run["scenario_history"])) if run.get("scenario_history") else ""
    if run.get("valuation_history"):
        scenario_html+="<details><summary>估值假设与计算明细</summary>"+"".join("<article><h3>"+e(v["method_name"])+"</h3><pre>"+e(json.dumps(v,ensure_ascii=False,indent=2))+"</pre></article>" for v in run["valuation_history"])+"</details>"
    if run.get("memo_revisions"):
        scenario_html+="<h2>报告修订记录</h2>"+"".join("<details><summary>第 "+str(v["revision"])+" 版 · "+e(v["change_note"])+"</summary><pre>"+e(json.dumps(v["memo"],ensure_ascii=False,indent=2))+"</pre></details>" for v in run["memo_revisions"])
    if run.get("attached_documents"):
        scenario_html+="<h2>对话补充材料</h2><p>已接入全文查阅，未自动覆盖已核验财务事实。</p>"+"".join("<pre>"+e(json.dumps(d,ensure_ascii=False,indent=2))+"</pre>" for d in run["attached_documents"])
    events="".join("<li>"+e(v["time"])+" · "+e(v["label"])+"："+e(v["detail"])+"</li>" for v in run["events"])
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>{e(run['company'])} · 研究底稿</title>
<style>body{{font:14px/1.85 system-ui,"Microsoft YaHei",sans-serif;color:#334155;margin:45px auto;padding:0 28px;max-width:980px}}header{{border-bottom:3px solid #6756b5;padding-bottom:24px}}.brand{{font-size:12px;letter-spacing:2px;color:#64748b}}h1{{font-size:29px;margin:14px 0}}h2{{margin-top:34px;font-size:20px;color:#475569}}h3{{font-size:15px}}.muted{{font-size:12px;color:#64748b}}table{{width:100%;border-collapse:collapse;text-align:right;font-variant-numeric:tabular-nums}}td,th{{padding:12px;border-bottom:1px solid #e2e8f0}}thead{{background:#f8fafc}}th:first-child{{text-align:left}}.summary,.counter{{padding:18px;background:#f6f5fc;border-left:3px solid #b7addf}}.thesis{{margin:22px 0}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font:11px/1.7 monospace;background:#f8fafc;padding:15px;border:1px solid #e2e8f0}}a{{color:#6554a5}}li{{margin:7px 0}}details{{margin:18px 0}}summary{{cursor:pointer;font-weight:600}}footer{{border-top:1px solid #e2e8f0;margin-top:35px;padding-top:16px}}@media print{{body{{margin:0;max-width:none;font-size:11px}}h2,h3{{break-after:avoid}}tr,.counter{{break-inside:avoid}}.print-hint{{display:none}}}}</style></head><body>
<header><div class="brand">研序 RESEARCH DESK · {e(memo.get('generator_version',run['version']))} · 报告第 {run.get('report_revision',1)} 版</div><h1>{e(memo.get('title') or run['company']+' · '+str(req['year'])+' 年财务研究')}</h1>
<p>{e(req['question'])}</p><p class="muted">截止日 {req['as_of']} · {'样例回放' if req['mode']=='sample' else '实时研究'} · {e(run['state'])} · 模型状态 {e(run['model']['status'])}</p><p class="muted print-hint">浏览器按 Ctrl + P 可打印或保存 PDF。</p></header>
<h2>核心财务事实</h2><p class="muted">人民币亿元，年度合并报表。归母净利润为归属于母公司股东口径。</p>
<table><thead><tr><th>指标</th><th>{req['year']}</th><th>{req['year']-1}</th><th>同比</th><th>本期来源状态</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<h2>{e(memo.get('title','研究判断 · 待复核'))}</h2><p><strong>{e(memo.get('stance',''))}</strong></p><p class="summary">{e(memo.get('summary','研究尚未完成'))}</p>{''.join(sections)}
<h2>继续研究的问题</h2><ul>{''.join('<li>'+e(q)+'</li>' for q in memo.get('questions',[]))}</ul>
<h2>数据与方法限制</h2><ul>{''.join('<li>'+e(q)+'</li>' for q in limitations)}</ul>
{scenario_html}<details><summary>计算过程与原始字段</summary>{calc_html}{''.join(sources)}</details>
<details><summary>运行记录</summary><ul class="muted">{events}</ul></details><footer class="muted">Run ID: {e(run['id'])} · 数据、计算与研究判断分别保存。完整原始响应见证据包。</footer></body></html>"""
