"""Read-only report/scenario relationships; never rewrite an earlier report."""
from copy import deepcopy
from .valuation import same_result


def valuation_snapshot(run):
    """Capture the scenarios available to a generation call, before model latency."""
    return {"captured_at": run.get("updated_at"),
            "scenarios": deepcopy(run.get("valuation_history", []))}


def referenced_valuation_ids(memo):
    ids = [i for item in memo.get("sections", []) + memo.get("theses", [])
           for i in item.get("evidence_ids", []) if isinstance(i, str)]
    ids += [s.get("id", "") for s in memo.get("sources", []) if s.get("kind") == "valuation"]
    return list(dict.fromkeys(i.removeprefix("valuation-") for i in ids if i.startswith("valuation-")))


def link_report_valuations(memo, snapshot):
    linked = deepcopy(memo)
    linked["valuation_context"] = {"schema_version": 1, **deepcopy(snapshot),
        "referenced_ids": referenced_valuation_ids(memo)}
    return linked


def report_valuation_status(run):
    """Compare each method with references, falling back to frozen generation inputs.

    IDs locate scenarios; semantic comparison prevents equivalent resubmissions from
    creating stale-report warnings. Legacy reports without links stay uncertain.
    """
    memo = run.get("memo")
    result = {"state": "no_report", "message": "尚无报告", "basis": "unknown",
              "report_revision": run.get("report_revision"), "items": []}
    if not memo:
        return result
    history = run.get("valuation_history", [])
    if not history:
        return {**result, "state": "no_valuations", "message": "尚未保存估值情景"}
    context = memo.get("valuation_context") or {}
    has_snapshot = context.get("schema_version") == 1 and isinstance(context.get("scenarios"), list)
    snapshot = context.get("scenarios", []) if has_snapshot else []
    catalog = {v["id"]: v for v in history}
    catalog.update({v["id"]: v for v in snapshot})
    reference_ids = referenced_valuation_ids(memo)
    if has_snapshot:
        reference_ids = list(dict.fromkeys(reference_ids + context.get("referenced_ids", [])))
    references = [catalog[i] for i in reference_ids if i in catalog]
    latest = {v["method"]: v for v in history}
    result["basis"] = "references" if references else "snapshot" if has_snapshot else "unknown"
    for method, current in latest.items():
        reported = [v for v in references if v["method"] == method]
        if not reported and has_snapshot:
            reported = [v for v in snapshot if v["method"] == method][-1:]
        if reported:
            state = "current" if any(same_result(v, current) for v in reported) else "changed"
        else:
            state = "changed" if has_snapshot else "unlinked"
        result["items"].append({"method": method, "method_name": current.get("method_name", method.upper()),
            "state": state, "reported_ids": [v["id"] for v in reported], "latest_id": current["id"],
            "latest_created_at": current.get("created_at"),
            "reported_assumptions": [v.get("assumptions", {}) for v in reported],
            "latest_assumptions": current.get("assumptions", {})})
    changed = [i["method_name"] for i in result["items"] if i["state"] == "changed"]
    unlinked = any(i["state"] == "unlinked" for i in result["items"])
    if changed:
        result.update(state="changed", message="报告尚未纳入最新 " + "、".join(changed) + " 情景，请对照假设；原报告内容保留。")
        if unlinked:
            result["message"] += "其他方法缺少完整关联，无法确认是否已纳入。"
    elif unlinked:
        result.update(state="unlinked", message="旧报告未记录完整估值关联，无法确认是否纳入当前情景，请对照。")
    else:
        result.update(state="current", message="当前情景与报告引用或生成时快照一致；快照不代表报告已逐项讨论。")
    return result
