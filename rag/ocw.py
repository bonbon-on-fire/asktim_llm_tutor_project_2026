"""OCW source reader for RAG ingestion (best-effort crawler).

Reads a course's ``online_link.txt`` (its MIT OpenCourseWare URL), crawls pages
under the same ``/courses/<slug>/`` path, strips boilerplate, and returns each
page as a labeled ``(source, text)`` document. Best-effort: OCW page structure
varies, so this is defensive (timeouts, per-page try/except, page cap, polite
delay) and the local reader remains the reliable fallback.

``requests`` and ``beautifulsoup4`` are imported lazily so that ``--source local``
ingestion works even if BeautifulSoup is not installed.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_CURRICULUM_ROOT = _REPO_ROOT / "curriculum"

Doc = tuple[str, str]

_USER_AGENT = "AskTIM-RAG/1.0 (+educational tutor; contact course staff)"
_SKIP_EXT = (".pdf", ".zip", ".jpg", ".jpeg", ".png", ".gif", ".mp4", ".mov", ".srt", ".vtt")


def read_online_link(course: str, curriculum_root: Path | str | None = None) -> str | None:
    """Return the first non-empty URL in the course's ``online_link.txt``, or None."""
    root = Path(curriculum_root) if curriculum_root is not None else _DEFAULT_CURRICULUM_ROOT
    path = root / course / "online_link.txt"
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line
    return None


def _course_prefix(url: str) -> str:
    """The ``/courses/<slug>/`` path prefix that in-scope pages must share."""
    parsed = urlparse(url)
    parts = parsed.path.strip("/").split("/")
    # .../courses/<slug>/...  ->  /courses/<slug>/
    if "courses" in parts:
        i = parts.index("courses")
        slug = parts[i : i + 2]
        return "/" + "/".join(slug) + "/"
    return parsed.path if parsed.path.endswith("/") else parsed.path + "/"


def _extract_text(html: str) -> str:
    from bs4 import BeautifulSoup  # lazy

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript", "form"]):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.body or soup
    text = main.get_text(separator="\n")
    # Collapse runs of blank lines / trailing whitespace.
    lines = [ln.strip() for ln in text.splitlines()]
    text = "\n".join(ln for ln in lines if ln)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def load_ocw_docs(
    course: str,
    *,
    curriculum_root: Path | str | None = None,
    max_pages: int = 40,
    delay_seconds: float = 0.5,
    min_chars: int = 200,
) -> list[Doc]:
    """Crawl the course's OCW site and return labeled page documents.

    Returns ``[]`` (and prints a hint) if there's no ``online_link.txt`` or the
    network/parse fails — callers should treat OCW as best-effort.
    """
    import time

    import requests  # lazy

    base = read_online_link(course, curriculum_root)
    if not base:
        return []

    prefix = _course_prefix(base)
    host = urlparse(base).netloc
    session = requests.Session()
    session.headers["User-Agent"] = _USER_AGENT

    seen: set[str] = set()
    queue: list[str] = [base]
    docs: list[Doc] = []

    while queue and len(docs) < max_pages:
        url = queue.pop(0)
        norm = url.split("#")[0].rstrip("/")
        if norm in seen:
            continue
        seen.add(norm)
        try:
            resp = session.get(url, timeout=15)
            if resp.status_code != 200 or "text/html" not in resp.headers.get("content-type", ""):
                continue
            html = resp.text
        except Exception:
            continue

        text = _extract_text(html)
        if len(text) >= min_chars:
            label_tail = urlparse(url).path.strip("/").split("/courses/")[-1]
            docs.append((f"ocw:{label_tail}", text))

        # Enqueue same-course in-scope links.
        from bs4 import BeautifulSoup  # lazy

        for a in BeautifulSoup(html, "html.parser").find_all("a", href=True):
            link = urljoin(url, a["href"]).split("#")[0]
            parsed = urlparse(link)
            if parsed.netloc != host:
                continue
            if not parsed.path.startswith(prefix):
                continue
            if parsed.path.lower().endswith(_SKIP_EXT):
                continue
            if link.split("#")[0].rstrip("/") not in seen:
                queue.append(link)

        time.sleep(delay_seconds)

    return docs
