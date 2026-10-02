"""Public annual statements, normalized to the same audited fact contract."""
import re
import httpx
from .providers import ProviderError

BASE="https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/"
ENDPOINTS={"income":"lrbAjaxNew","cashflow":"xjllbAjaxNew"}

class Eastmoney:
    def __init__(self,ticker):
        symbol,exchange=ticker.split(".")
        self.ticker=ticker
        self.code=exchange+symbol
        self.source_url=BASE+"Index?type=web&code="+self.code.lower()
        try:
            response=httpx.get(self.source_url,timeout=20)
            response.raise_for_status()
            tag=re.search(r'<input[^>]*id=["\']hidctype["\'][^>]*>',response.text)
            match=re.search(r'value=["\'](\d+)["\']',tag.group(0)) if tag else None
            if not match: raise ValueError()
            self.company_type=match.group(1)
        except (httpx.HTTPError,ValueError):
            raise ProviderError("公开财务接口未能识别该公司；可切换 Tushare 或上传披露文件") from None

    def statement(self,api,year):
        params={"companyType":self.company_type,"reportDateType":0,"reportType":1,
                "code":self.code,"dates":f"{year}-12-31"}
        try:
            response=httpx.get(BASE+ENDPOINTS[api],params=params,timeout=25)
            response.raise_for_status()
            data=response.json().get("data") or []
            rows=[]
            for record in data:
                if record.get("SECURITY_CODE")!=self.ticker[:6]: raise ValueError()
                # Revised values are not treated as available before their update date.
                announced=max(str(record.get("NOTICE_DATE") or ""),str(record.get("UPDATE_DATE") or ""))
                row={"ts_code":self.ticker,"name":record.get("SECURITY_NAME_ABBR"),
                     "end_date":str(record.get("REPORT_DATE") or "")[:10].replace("-",""),
                     "ann_date":announced[:10].replace("-",""),"report_type":"1",
                     "_source":"eastmoney","_source_url":self.source_url,"_raw":record}
                if api=="income": row.update(revenue=record.get("OPERATE_INCOME"),n_income_attr_p=record.get("PARENT_NETPROFIT"))
                else: row["n_cashflow_act"]=record.get("NETCASH_OPERATE")
                rows.append(row)
            return rows
        except (httpx.HTTPError,ValueError,KeyError,TypeError):
            raise ProviderError("公开财务接口响应异常或暂时限流，未补造缺失数据") from None
