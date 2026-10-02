"""Daily full-market directory with debounced client lookup and explicit fallback."""
import json
import threading
import time
from datetime import datetime,timezone
from difflib import SequenceMatcher
from .config import DATA
from .providers import tushare,ProviderError
from . import store

LOCK=threading.Lock()
last_attempt=0.0

def directory(refresh=False):
    global last_attempt
    path=DATA/"securities.json"
    with LOCK:
        cached=json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
        fresh=cached and time.time()-cached.get("timestamp",0)<86400
        if fresh and not refresh: return cached|{"stale":False}
        if time.time()-last_attempt<60:
            if cached: return cached|{"stale":not fresh,"note":"已使用最近缓存；目录刷新间隔至少一分钟"}
            return fallback("尚无全市场目录；配置 Tushare 后可刷新，或直接填写完整代码")
        last_attempt=time.time()
        try:
            rows=tushare("stock_basic",{"list_status":"L"},"ts_code,symbol,name,fullname,cnspell,industry,exchange")
            if not rows or any(not r.get("ts_code") or not r.get("name") for r in rows): raise ProviderError("证券目录返回为空")
            value={"items":rows,"timestamp":time.time(),"updated_at":datetime.now(timezone.utc).isoformat(),
                   "source":"Tushare 在市 A 股证券目录","stale":False}
            DATA.mkdir(parents=True,exist_ok=True)
            temp=path.with_suffix(".tmp")
            temp.write_text(json.dumps(value,ensure_ascii=False),encoding="utf-8");temp.replace(path)
            return value
        except ProviderError as error:
            if cached: return cached|{"stale":True,"note":"在线刷新失败，使用已保存目录："+str(error)}
            return fallback(str(error)+"；可直接填写完整代码")

def fallback(note):
    items={}
    for run in store.list_runs():
        ticker=run["request"]["ticker"]
        items[ticker]={"ts_code":ticker,"symbol":ticker[:6],"name":run["company"],"cnspell":""}
    return {"items":list(items.values()),"updated_at":None,"source":"本机历史研究（非全市场）","stale":True,"note":note}

def search(query="",refresh=False):
    catalog=directory(refresh)
    q=query.strip().casefold()
    found=[]
    for row in catalog["items"]:
        texts=[str(row.get(k) or "").casefold() for k in ("name","fullname","ts_code","symbol","cnspell")]
        if not q: score=0
        elif q in texts: score=100
        elif any(v.startswith(q) for v in texts): score=90
        elif any(q in v for v in texts): score=80
        else:
            score=max(SequenceMatcher(None,q,v).ratio() for v in texts[:2])*50 if len(q)>1 else 0
            if score<35: continue
        found.append((score,row))
    found.sort(key=lambda pair:(-pair[0],pair[1]["ts_code"]))
    return {k:v for k,v in catalog.items() if k not in ("items","timestamp")}|{"items":[r for _,r in found[:15]],"total":len(catalog["items"])}
