"""Tests of the single download with blocklist (investment spec A5.1).

No network. The blocked hostnames appear here only as strings; no test opens a
connection. Permitted addresses end in ``.invalid`` (RFC 2606) and do not
exist.

The most important test is ``test_blocked_address_opens_no_connection``: the
ban means "no automated access", so not even the request may go out.
"""

from __future__ import annotations

import hashlib
import io
import urllib.request

import pytest

from trading_app.sources import documents
from trading_app.sources.documents import (
    DocumentError,
    ForbiddenSourceError,
    check_url,
    download_document,
)

PDF = b"%PDF-1.7\n% placeholder, not a real document\n%%EOF\n"
ALLOWED = "https://issuer.invalid/documents/kid.pdf"


class FakeResponse(io.BytesIO):
    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_: object) -> None:
        pass


@pytest.fixture
def fake_opener(monkeypatch):
    """Replaces build_opener. Records which handlers it was built with."""
    log: dict[str, list] = {"handler": [], "urls": []}

    def install(content: bytes = PDF):
        class Opener:
            def open(self, url, timeout=None):  # noqa: ARG002
                log["urls"].append(url)
                return FakeResponse(content)

        def build(*handlers):
            log["handler"].extend(handlers)
            return Opener()

        monkeypatch.setattr(urllib.request, "build_opener", build)
        return log

    return install


# ---------------------------------------------------------------------------
# Blocklist — hard-coded
# ---------------------------------------------------------------------------


class TestBlocklist:
    @pytest.mark.parametrize(
        "url",
        [
            "https://www.justetf.com/document.pdf",
            "https://justetf.com/document.pdf",
            "https://WWW.JUSTETF.COM/document.pdf",
            "https://www.justetf.de/document.pdf",
            "https://www.vanguard.de/document.pdf",
            "https://global.vanguard.com/document.pdf",
            "https://www.de.vanguard/document.pdf",
            "https://www.vanguardinvestor.co.uk/document.pdf",
            "https://www.justetf.com:443/document.pdf",
            "https://www.justetf.com./document.pdf",  # trailing dot
            "https://issuer.invalid@www.justetf.com/document.pdf",  # userinfo deceives
        ],
    )
    def test_blocked_providers(self, url) -> None:
        with pytest.raises(ForbiddenSourceError, match="blocked"):
            check_url(url)

    def test_message_names_reason_and_way_out(self) -> None:
        with pytest.raises(ForbiddenSourceError) as error:
            check_url("https://www.justetf.com/document.pdf")
        text = str(error.value)
        assert "A5.1" in text
        assert "by hand" in text

    def test_similar_name_inside_a_label_is_not_blocked(self) -> None:
        """Blocking goes by label start, not by substring anywhere."""
        check_url("https://www.myvanguard-comparison.invalid/document.pdf")

    @pytest.mark.parametrize(
        "url",
        [
            ALLOWED,
            "https://issuer.invalid/DOCUMENTS/KID.PDF",
            "https://issuer.invalid/kid.pdf#page=2",
        ],
    )
    def test_single_pdf_at_the_issuer_is_allowed(self, url) -> None:
        check_url(url)


class TestSinglePdfOnly:
    @pytest.mark.parametrize(
        "url",
        [
            "https://issuer.invalid/api/products?format=json",
            "https://issuer.invalid/kid.pdf?lang=de",
            "https://issuer.invalid/product/overview",
            "https://issuer.invalid/",
        ],
    )
    def test_queries_and_pages_are_forbidden(self, url) -> None:
        """Internal APIs cannot be blocked by domain — by address form they can."""
        with pytest.raises(ForbiddenSourceError, match="PDF"):
            check_url(url)

    @pytest.mark.parametrize(
        "url", ["http://issuer.invalid/kid.pdf", "ftp://issuer.invalid/kid.pdf", "kid.pdf"]
    )
    def test_https_only(self, url) -> None:
        with pytest.raises(ForbiddenSourceError, match="https"):
            check_url(url)


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


class TestDownload:
    def test_blocked_address_opens_no_connection(self, monkeypatch, tmp_path) -> None:
        def forbidden(*_):
            raise AssertionError("Connection opened although the address is blocked")

        monkeypatch.setattr(urllib.request, "build_opener", forbidden)
        with pytest.raises(ForbiddenSourceError):
            download_document("https://www.justetf.com/document.pdf", tmp_path)
        assert list(tmp_path.iterdir()) == []

    def test_pdf_is_stored_under_its_hash(self, fake_opener, tmp_path) -> None:
        log = fake_opener(PDF)
        path = download_document(ALLOWED, tmp_path / "documents")
        assert path.read_bytes() == PDF
        assert path.name == hashlib.sha256(PDF).hexdigest() + ".pdf"
        assert log["urls"] == [ALLOWED]

    def test_redirects_are_checked(self, fake_opener, tmp_path) -> None:
        """Without its own handler urllib would follow a redirect unchecked."""
        log = fake_opener(PDF)
        download_document(ALLOWED, tmp_path)
        assert documents._CheckedRedirect in log["handler"]

    def test_non_pdf_is_not_stored(self, fake_opener, tmp_path) -> None:
        fake_opener(b'{"products": []}')
        with pytest.raises(DocumentError, match="no PDF"):
            download_document(ALLOWED, tmp_path)
        assert list(tmp_path.iterdir()) == []

    def test_oversized_response_is_rejected(self, fake_opener, monkeypatch, tmp_path) -> None:
        monkeypatch.setattr(documents, "_MAX_SIZE", 10)
        fake_opener(PDF)
        with pytest.raises(DocumentError, match="larger than"):
            download_document(ALLOWED, tmp_path)


class TestRedirect:
    def _request(self) -> urllib.request.Request:
        return urllib.request.Request(ALLOWED)

    @pytest.mark.parametrize(
        "target",
        ["https://www.justetf.com/detour.pdf", "https://global.vanguard.com/detour.pdf",
         "http://issuer.invalid/kid.pdf"],
    )
    def test_redirect_to_forbidden_target_aborts(self, target) -> None:
        handler = documents._CheckedRedirect()
        with pytest.raises(ForbiddenSourceError):
            handler.redirect_request(self._request(), None, 302, "Found", {}, target)

    def test_redirect_to_cdn_with_query_is_allowed(self) -> None:
        """Signed CDN addresses carry query parameters; the content is checked then."""
        handler = documents._CheckedRedirect()
        new = handler.redirect_request(
            self._request(), None, 302, "Found", {}, "https://cdn.invalid/kid.pdf?signature=abc"
        )
        assert new.full_url == "https://cdn.invalid/kid.pdf?signature=abc"
