import json
import time
from urllib.parse import urlparse
import httpx
from .config import settings

class ProviderError(Exception):
    pass

def tushare(api,params,fields):
    cfg=settings()
    if not cfg["token"]:
        raise ProviderError("未配置 Tushare Token")
    for attempt in range(2):
        try:
            response=httpx.post("https://api.tushare.pro",json={"api_name":api,"token":cfg["token"],"params":params,"fields":fields},timeout=25)
            response.raise_for_status()
            payload=response.json()
            if payload.get("code")!=0:
                raise ProviderError(f"Tushare {api} 未返回数据（权限、额度或参数错误，code={payload.get('code')}）")
            data=payload.get("data") or {}
            return [dict(zip(data.get("fields",[]),r)) for r in data.get("items",[])]
        except (httpx.TimeoutException,httpx.NetworkError):
            if attempt: raise ProviderError(f"Tushare {api} 网络请求失败，两次尝试后停止") from None
        except (httpx.HTTPStatusError,ValueError):
            raise ProviderError(f"Tushare {api} 响应异常，未取得有效数据") from None
    return []

def model_json(system,payload,max_tokens=2400,profile_id=None,reasoning=False):
    from .connections import resolve_model,validate_base
    cfg=resolve_model(profile_id)
    if not cfg["key"] and cfg["provider"]!="ollama":
        raise ProviderError("当前模型连接尚未配置 API Key，请在连接设置中填写")
    if not cfg["model"]: raise ProviderError("请先在连接设置中填写模型名称")
    validate_base(cfg["base"])
    started=time.monotonic()
    try:
        headers={"Content-Type":"application/json"}
        prompt=system+"\nReturn a valid JSON object only, no markdown fences."
        message={"role":"user","content":json.dumps(payload,ensure_ascii=False)}
        if cfg["protocol"]=="anthropic":
            headers.update({"x-api-key":cfg["key"],"anthropic-version":"2023-06-01"})
            endpoint="/messages"
            body={"model":cfg["model"],"system":prompt,"messages":[message],"max_tokens":max_tokens}
        else:
            if cfg["key"]: headers["Authorization"]="Bearer "+cfg["key"]
            endpoint="/chat/completions"
            body={"model":cfg["model"],"messages":[{"role":"system","content":prompt},message]}
            body["max_completion_tokens" if cfg["provider"]=="openai" else "max_tokens"]=max_tokens
            if cfg.get("json_mode",True): body["response_format"]={"type":"json_object"}
            if cfg["provider"]=="deepseek":
                body["thinking"]={"type":"enabled" if reasoning else "disabled"}
                if reasoning: body["max_tokens"]=max_tokens+8000
                else: body["temperature"]=0.1
        response=httpx.post(cfg["base"]+endpoint,headers=headers,json=body,timeout=180 if reasoning else 80)
        response.raise_for_status()
        data=response.json()
        if cfg["protocol"]=="anthropic":
            content="".join(b["text"] for b in data.get("content",[]) if b.get("type")=="text")
            stopped=data.get("stop_reason")=="max_tokens"
        else:
            content=data["choices"][0]["message"]["content"]
            stopped=data["choices"][0].get("finish_reason")=="length"
        if stopped:
            raise ProviderError("模型生成达到本次长度上限，未采用不完整草稿")
        content=content.strip();fence=chr(96)*3
        if content.startswith(fence): content=content.split("\n",1)[-1].rsplit(fence,1)[0].strip()
        value=json.loads(content)
        if not isinstance(value,dict): raise ValueError()
        return value,{"model":cfg["model"],"provider":cfg["provider"],"connection_id":cfg["id"],"reasoning_enabled":bool(reasoning and cfg["provider"]=="deepseek"),"elapsed_ms":int((time.monotonic()-started)*1000),"usage":data.get("usage",{})}
    except httpx.HTTPStatusError as error:
        raise ProviderError(f"模型接口返回 HTTP {error.response.status_code}；请检查当前服务的密钥、模型名和接口协议") from None
    except (httpx.HTTPError,ValueError,KeyError,IndexError):
        raise ProviderError("模型调用超时、请求失败或未返回有效 JSON；已保留财务证据，不生成无依据结论") from None

def list_models(profile_id):
    from .connections import resolve_model
    cfg=resolve_model(profile_id)
    headers={"x-api-key":cfg["key"],"anthropic-version":"2023-06-01"} if cfg["protocol"]=="anthropic" else ({"Authorization":"Bearer "+cfg["key"]} if cfg["key"] else {})
    try:
        response=httpx.get(cfg["base"]+"/models",headers=headers,timeout=15)
        response.raise_for_status()
        models=[v["id"] for v in response.json().get("data",[]) if isinstance(v.get("id"),str)]
        return {"models":sorted(models)[:500],"detail":"来自当前服务的模型列表"}
    except (httpx.HTTPError,ValueError,KeyError):
        raise ProviderError("该服务未返回模型列表；可按服务商提供的模型名称手动填写") from None
