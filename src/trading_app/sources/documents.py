"""Single download of public mandatory documents (KID, factsheet) — and nothing else.

A5.1 permits fetching public mandatory documents manually or as a single
download at low frequency. Forbidden are automated queries to justETF
(general terms § 3.1) and Vanguard (terms of use) as well as undocumented
internal issuer APIs (e.g. iShares). The ban therefore lives in the code, not
only in the docs:

1. **Blocklist.** If a label of the hostname starts with ``justetf`` or
   ``vanguard``, the address is rejected before any connection — also as the
   target of a redirect. Prefix rather than exact domain, because Vanguard
   appears under many names (``vanguard.de``, ``global.vanguard.com``,
   ``vanguardinvestor.co.uk``, its own top-level domain ``.vanguard``). Better
   to block one unrelated site too many than to let a forbidden one through.
2. **Single PDF documents only.** Only ``https``, the path ends in ``.pdf``,
   no query, and the response must start with ``%PDF-``. Internal APIs cannot
   be blocked by domain, because they sit on the same hosts as the permitted
   PDFs. The rule therefore admits only an address form that denotes a
   document and not a query.
3. **One address per call.** No loop, no link following.

Whatever cannot be reached this way, a human downloads in the browser and
enters the address in the source file (``instruments.load_source_file``).

Not settled, because A5.1 gives no number: what "low frequency" means.
"""

from __future__ import annotations

import hashlib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

__all__ = [
    "DocumentError",
    "ForbiddenSourceError",
    "check_url",
    "download_document",
]

# Label prefixes of blocked providers (A5.1).
_BLOCKED = ("justetf", "vanguard")

# A KID has three pages, a factsheet a few. Anything above that is not a
# mandatory document.
_MAX_SIZE = 50 * 1024 * 1024


class DocumentError(RuntimeError):
    """The download failed or did not return a PDF."""


class ForbiddenSourceError(DocumentError):
    """The address is forbidden for automated retrieval under A5.1."""


def _check_host(url: str) -> None:
    """https and blocklist. Applies to every redirect target too."""
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https":
        raise ForbiddenSourceError(f"Only https addresses, was {parts.scheme!r}: {url}")
    host = (parts.hostname or "").lower()
    if not host:
        raise ForbiddenSourceError(f"Address without a host: {url}")
    if any(label.startswith(_BLOCKED) for label in host.split(".")):
        raise ForbiddenSourceError(
            f"{host} is blocked. Automated queries to justETF (general terms § 3.1) and "
            "Vanguard (terms of use) are forbidden (investment spec A5.1). "
            "Download the document by hand in the browser and enter the address in the "
            "source file."
        )


def check_url(url: str) -> None:
    """Checks an address before the first retrieval.

    Raises:
        ForbiddenSourceError: Blocked provider, not https, or not a single
            PDF file.
    """
    _check_host(url)
    parts = urllib.parse.urlsplit(url)
    if parts.query or not parts.path.lower().endswith(".pdf"):
        raise ForbiddenSourceError(
            f"Single PDF documents only: the path must end in .pdf, without a query. "
            f"Was: {url}. Undocumented internal issuer APIs are forbidden (A5.1)."
        )


class _CheckedRedirect(urllib.request.HTTPRedirectHandler):
    """Checks every redirect target before it is called.

    Without this class urllib follows a redirect silently — a link via a URL
    shortener could end up at a blocked provider.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _check_host(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download_document(url: str, target_dir: str | Path, *, timeout: float = 30.0) -> Path:
    """Downloads exactly one public PDF and stores it.

    The file name is the SHA-256 of the content: the same version yields the
    same file, and a new version overwrites no old one.

    Args:
        url: Address of the document (https, path ending in ``.pdf``, no query).
        target_dir: Folder to store it in — outside iCloud, e.g.
            ``~/claude-local/trading-app/documents/``.
        timeout: Time limit in seconds.

    Returns:
        Path of the stored file.

    Raises:
        ForbiddenSourceError: Address or redirect target is forbidden. In
            that case there was no connection to the forbidden host.
        DocumentError: Network or HTTP error, too large, or not a PDF.
    """
    check_url(url)
    opener = urllib.request.build_opener(_CheckedRedirect)
    try:
        with opener.open(url, timeout=timeout) as response:
            content = response.read(_MAX_SIZE + 1)
    except urllib.error.HTTPError as error:
        raise DocumentError(f"HTTP {error.code} for {url}") from error
    except urllib.error.URLError as error:
        raise DocumentError(f"Network error for {url}: {error.reason}") from error

    if len(content) > _MAX_SIZE:
        raise DocumentError(f"{url} is larger than {_MAX_SIZE} bytes — not a mandatory document")
    if not content.startswith(b"%PDF-"):
        raise DocumentError(
            f"{url} returned no PDF (starts with: {content[:20]!r}). Nothing stored."
        )

    folder = Path(target_dir).expanduser()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{hashlib.sha256(content).hexdigest()}.pdf"
    path.write_bytes(content)
    return path
