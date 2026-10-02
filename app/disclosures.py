"""Public annual-report discovery. Does not use a Tushare token or LLM-generated URLs."""
import html
import re
from datetime import date,datetime,timezone,timedelta
from urllib.parse import urlparse
import httpx
from . import documents,store
from .providers import ProviderError

HEADERS={"User-Agent":"Mozilla/5.0","Referer":"https://www.cninfo.com.cn/"}
ROOT="https://www.cninfo.com.cn"


def annual_candidates(ticker,year,as_of=None):
    if not re.fullmatch(r"\d{6}\.(SZ|SH|BJ)",ticker): raise ValueError("证券代码无效")
    cutoff=date.fromisoformat(as_of) if as_of else date.today()
    if not isinstance(year,int) or not 2000<=year<=cutoff.year or cutoff>date.today(): raise ValueError("年度或截止日无效")
    code,exchange=ticker.split(".")
    if cutoff<date(year+1,1,1): return {"items":[],"note":"截止日早于年度结束后的披露期"}
    try:
        with httpx.Client(timeout=25,headers=HEADERS) as client:
            r=client.post(ROOT+"/new/information/topSearch/query",data={"keyWord":code,"maxNum":"10"});r.raise_for_status()
            matches=[v for v in r.json() if v.get("code")==code and v.get("category")=="A股"]
            if len(matches)!=1: raise ProviderError("公开披露目录未能唯一确认证券，请使用上传 PDF")
            security=matches[0];items=[];truncated=False
            for page in range(1,4):
                r=client.post(ROOT+"/new/hisAnnouncement/query",data={"pageNum":str(page),"pageSize":"100",
                    "column":{"SH":"sse","SZ":"szse","BJ":"bse"}[exchange],"tabName":"fulltext",
                    "stock":code+","+security["orgId"],"searchkey":"年度报告","category":"",
                    "seDate":f"{year+1}-01-01~{cutoff.isoformat()}","isHLtitle":"false"})
                r.raise_for_status();payload=r.json()
                for row in payload.get("announcements") or []:
                    title=html.unescape(re.sub(r"<[^>]+>","",row.get("announcementTitle", "")))
                    compact=re.sub(r"\s+","",title)
                    if row.get("secCode")!=code or not re.search(fr"{year}年?年度报告",compact): continue
                    if any(s in compact for s in ("摘要","取消","英文","翻译","更正公告","补充公告","提示性公告")): continue
                    path=row.get("adjunctUrl","")
                    if not re.fullmatch(r"finalpage/\d{4}-\d{2}-\d{2}/\d+\.pdf",path,re.I): continue
                    published=datetime.fromtimestamp(int(row["announcementTime"])/1000,timezone(timedelta(hours=8))).date()
                    if published>cutoff: continue
                    items.append({"announcement_id":str(row["announcementId"]),"title":title,"ticker":ticker,"year":year,
                        "company":security.get("zwjc"),"announced_date":published.isoformat(),
                        "source_url":"https://static.cninfo.com.cn/"+path,"source":"巨潮资讯公开披露"})
                if page*100>=int(payload.get("totalAnnouncement") or 0): break
                truncated=page==3
    except ProviderError: raise
    except (httpx.HTTPError,ValueError,KeyError,TypeError):
        raise ProviderError("巨潮资讯年报查询暂不可用或返回格式变化；可稍后重试，或直接上传 PDF。与 Tushare Token 无关。") from None
    unique={v["announcement_id"]:v for v in items}
    ordered=sorted(unique.values(),key=lambda x:(x["announced_date"],int(x["announcement_id"])),reverse=True)
    return {"items":ordered,"truncated":truncated,"note":"只返回匹配公司、年度和截止日的年报全文；公开站点可能更新同一公告的附件，不能保证严格历史版本。"}


def fetch_annual(ticker,year,as_of=None):
    found=annual_candidates(ticker,year,as_of)
    if not found["items"]: raise ValueError("未找到当前截止日前匹配的年报全文。可上传 PDF；未将摘要或半年报作为替代。")
    candidate=found["items"][0];url=candidate["source_url"]
    for saved in store.list_documents():
        if saved.get("source_url")==url and saved["ticker"]==ticker and saved["year"]==year and saved.get("announced_date")==candidate["announced_date"]:
            documents.ensure_index(saved)
            return saved
    parsed=urlparse(url)
    if parsed.scheme!="https" or parsed.netloc!="static.cninfo.com.cn": raise ValueError("年报下载来源无效")
    try:
        with httpx.Client(timeout=60,headers=HEADERS,follow_redirects=False) as client:
            with client.stream("GET",url) as response:
                response.raise_for_status();chunks=[];size=0
                for chunk in response.iter_bytes():
                    size+=len(chunk)
                    if size>documents.MAX_BYTES: raise ValueError("年报超过 100 MB，可自行下载并精简后上传")
                    chunks.append(chunk)
    except httpx.HTTPError:
        raise ProviderError("年报链接已找到，但公开站点下载失败，请重试或手动上传。与 Tushare Token 无关。") from None
    doc=documents.register_pdf(b"".join(chunks),ticker,year,candidate["title"]+".pdf",candidate["announced_date"],
        source_url=url,kind="public_report",company=candidate.get("company"),annual=True)
    return doc
