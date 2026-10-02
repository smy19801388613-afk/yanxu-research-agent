import pytest

from app import public_pdf


URL = "https://static.cninfo.com.cn/finalpage/2026-04-28/1225213079.PDF"


def fetched(monkeypatch, pages=None, url=URL, content=b"%PDF-stub"):
    calls = []
    def fetch(address, **kwargs):
        calls.append((address, kwargs))
        return {"url": url, "content": content, "is_pdf": True, "content_type": "application/pdf"}
    monkeypatch.setattr(public_pdf.web_research, "_fetch", fetch)
    if pages is not None:
        monkeypatch.setattr(public_pdf, "_extract_pages", lambda raw: (pages, []))
    return calls


@pytest.mark.parametrize("url", [
    "https://cninfo.com.cn.evil.example/a.pdf", "https://evilcninfo.com.cn/a.pdf",
    "https://example.com/a.pdf", "http://127.0.0.1/a.pdf", "file:///tmp/a.pdf",
    "https://user:secret@static.cninfo.com.cn/a.pdf", "https://static.cninfo.com.cn:8912/a.pdf",
])
def test_rejects_nonofficial_urls_before_fetch(monkeypatch, url):
    calls = fetched(monkeypatch, ["营业收入 " * 20])
    assert public_pdf.read(url)["status"] == "error"
    assert not calls


def test_reads_page_locators_and_url_dates_without_writing_attachments(monkeypatch):
    calls = fetched(monkeypatch, ["会计差错更正公告 本次更正主要将总额法更正为净额法。" * 3,
                                 "2025 半年度 营业收入 调整前 653057269.10 调整后 592472821.09"])
    result = public_pdf.read(URL + "#page=2", "2026-10-02", ["营业收入 净额法"])
    assert result["status"] == "ok"
    assert result["published_at"] == "2026-04-28"
    assert calls == [(URL, {"binary_pdf": True, "max_bytes": 12 * 1024 * 1024})]
    assert [row["url"] for row in result["results"]] == [URL + "#page=1", URL + "#page=2"]
    assert all(row["extraction"] == "public_pdf_text" for row in result["results"])
    assert "592472821.09" in result["results"][1]["text"]


def test_future_original_date_is_excluded_before_download(monkeypatch):
    calls = fetched(monkeypatch, ["收入" * 30])
    assert public_pdf.read(URL, "2026-04-27")["status"] == "excluded"
    assert not calls


def test_future_redirect_is_excluded_before_parse(monkeypatch):
    fetched(monkeypatch, url="https://static.cninfo.com.cn/finalpage/2026-11-01/1.PDF")
    monkeypatch.setattr(public_pdf, "_extract_pages", lambda raw: pytest.fail("future PDF parsed"))
    assert public_pdf.read(URL, "2026-10-02")["status"] == "excluded"


def test_external_redirect_is_rejected_even_if_transport_is_mocked(monkeypatch):
    fetched(monkeypatch, url="https://example.com/report.pdf")
    assert public_pdf.read(URL)["status"] == "error"


def test_unknown_date_not_inferred_from_filename_or_report_body(monkeypatch):
    url = "https://www.csrc.gov.cn/files/2026-08-26-report.pdf"
    fetched(monkeypatch, ["2026年8月26日 2026 半年度报告 营业收入 123456.78"], url=url)
    result = public_pdf.read(url, "2026-10-02")
    assert result["status"] == "ok"
    assert result["published_at"] is None and result["date_basis"] is None
    assert result["results"][0]["date_status"] == "unknown"


def test_scanned_pages_never_become_read_evidence(monkeypatch):
    fetched(monkeypatch, ["", "2", "企业名称"])
    result = public_pdf.read(URL)
    assert result["status"] == "needs_ocr"
    assert not result["results"]
    assert result["pages_without_usable_text"] == [1, 2, 3]


def test_keywords_reach_late_financial_notes_with_bounded_excerpts(monkeypatch):
    pages = ["某公司半年度报告 证券代码 300271 董事会保证内容准确完整。"]
    pages += ["普通经营说明和会计政策，无相关财务数据。" * 20 for _ in range(25)]
    pages += ["段落背景。" * 1200 + "信用减值损失 34215806.93 上期51708918.38\n资产减值损失 115186719.43 上期123256464.88" + "末尾。" * 100]
    fetched(monkeypatch, pages)
    result = public_pdf.read(URL, queries=["信用减值损失 资产减值损失"])
    assert len(result["results"]) == 12
    assert 1 in result["selected_pages"] and 27 in result["selected_pages"]
    match = next(row for row in result["results"] if row["page"] == 27)
    assert "51708918.38" in match["text"]
    assert len(match["text"]) <= 5000 and match["excerpt_truncated"]


def test_size_and_html_errors_return_no_false_evidence(monkeypatch):
    fetched(monkeypatch, content=b"%PDF-" + b"x" * public_pdf.MAX_DOWNLOAD_BYTES)
    assert public_pdf.read(URL)["status"] == "error"
    monkeypatch.setattr(public_pdf.web_research, "_fetch", lambda *args, **kwargs: {"url": URL, "is_pdf": False, "text": "captcha"})
    result = public_pdf.read(URL)
    assert result["status"] == "error" and not result["results"]


def test_malformed_pdf_is_explicit_error(monkeypatch):
    fetched(monkeypatch, content=b"%PDF-corrupt")
    result = public_pdf.read(URL)
    assert result["status"] == "error" and not result["results"]


def test_page_limit_checked_before_page_access(monkeypatch):
    class TooLarge:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def __len__(self): return 261
        def __getitem__(self, index): pytest.fail("page was opened before page limit check")
    monkeypatch.setattr(public_pdf.pypdfium2, "PdfDocument", lambda _: TooLarge())
    with pytest.raises(ValueError, match="260"):
        public_pdf._extract_pages(b"%PDF-stub")


def test_invalid_cutoff_rejected_before_fetch(monkeypatch):
    calls = fetched(monkeypatch, ["营业收入 " * 20])
    result = public_pdf.read(URL, "2026-99-30")
    assert result["status"] == "error" and not calls
