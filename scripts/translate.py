#!/usr/bin/env python3
"""Translate Hugo posts from Mandarin to English via an LLM.

For each `<post>.md` under content/, generates a sibling `<post>.en.md`. Caches by
hashing the source content; re-runs only when the source changes. Markdown
shortcodes ({{< ... >}}), HTML tags, code blocks, image markup, and URLs are
segmented out before the LLM call so the model only sees prose. `caption="..."`
values inside shortcodes are extracted and translated separately.

Two providers, selected by LLM_PROVIDER (auto-detected if unset):

    openai (default when LLM_BASE_URL is set):
        LLM_BASE_URL   OpenAI-compatible endpoint, e.g. http://192.168.1.104:1234/v1
        LLM_MODEL      Model id, e.g. google/gemma-4-e4b
        LLM_API_KEY    Optional, defaults to "local"

    gemini (default when GEMINI_API_KEY is set):
        GEMINI_API_KEY Google AI Studio key
        GEMINI_MODEL   Optional, defaults to gemini-flash-latest

Optional rate limit (sliding 60s window):
    LLM_RPM        Max requests per minute. 0 disables. Default: 5 for gemini, 0 for openai.

Usage:
    uv run scripts/translate.py                          # all posts
    uv run scripts/translate.py content/explorations/mazu.md
    uv run scripts/translate.py --dry-run <path>         # show segments, no API calls
    uv run scripts/translate.py --force <path>           # ignore cache
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_ROOT = REPO_ROOT / "content"

# Hugo language codes we recognise as filename suffixes (e.g. "post.en.md").
KNOWN_LANGS = ("zh-Hant", "zh", "en")
LANG_NAMES = {
    "en": "English",
    "zh": "Chinese",
    "zh-Hant": "Traditional Chinese (Mandarin)",
}


# --- Frontmatter handling -------------------------------------------------

@dataclass
class FrontMatter:
    delim: str   # '+++' (TOML) or '---' (YAML)
    text: str    # raw frontmatter content between the delimiters
    body: str    # body following the closing delimiter


def split_frontmatter(text: str) -> FrontMatter:
    if text.startswith("+++"):
        delim = "+++"
    elif text.startswith("---"):
        delim = "---"
    else:
        raise ValueError("file has no recognised frontmatter delimiter")
    end = text.index(delim, len(delim))
    fm_text = text[len(delim):end]
    body = text[end + len(delim):].lstrip("\n")
    return FrontMatter(delim, fm_text, body)


_TITLE_LINE = re.compile(
    r'^(?P<key>title\s*)(?P<sep>[:=])(?P<sp>\s*)["\'](?P<val>[^"\']*)["\']',
    re.MULTILINE,
)
_FIELD_VALUE = re.compile(
    r'^{key}\s*[:=]\s*["\']([^"\']*)["\']',
)
_HASH_LINE = re.compile(
    r'^source_hash\s*[:=]\s*["\']([^"\']*)["\']',
    re.MULTILINE,
)


def get_title(fm_text: str) -> str | None:
    m = _TITLE_LINE.search(fm_text)
    return m.group("val") if m else None


def get_field(fm_text: str, key: str) -> str | None:
    pat = re.compile(
        rf'^{re.escape(key)}\s*[:=]\s*["\']([^"\']*)["\']',
        re.MULTILINE,
    )
    m = pat.search(fm_text)
    return m.group(1) if m else None


def get_source_hash(fm_text: str) -> str | None:
    m = _HASH_LINE.search(fm_text)
    return m.group(1) if m else None


def replace_title(fm_text: str, new_title: str) -> str:
    quoted = json.dumps(new_title, ensure_ascii=False)

    def sub(m: re.Match[str]) -> str:
        return f"{m.group('key')}{m.group('sep')}{m.group('sp')}{quoted}"

    return _TITLE_LINE.sub(sub, fm_text, count=1)


def upsert_source_hash(fm_text: str, delim: str, source_hash: str) -> str:
    sep = "=" if delim == "+++" else ":"
    line = f'source_hash {sep} "{source_hash}"'
    if _HASH_LINE.search(fm_text):
        return _HASH_LINE.sub(line, fm_text)
    return fm_text.rstrip() + "\n" + line + "\n"


# --- Body segmentation ----------------------------------------------------
#
# Spans we hand to the LLM are bounded by spans we keep verbatim. Order in the
# pattern matters: longer / more specific patterns first.

_TOKEN_RE = re.compile(
    r"(?P<codeblock>```[\s\S]*?```)"
    r"|(?P<inline_code>`[^`\n]+`)"
    r"|(?P<shortcode>\{\{<[\s\S]*?>\}\})"
    r"|(?P<html>(?:<[a-zA-Z/!][^>]*>))"
    r"|(?P<image>!\[[^\]]*\]\([^)]+\))"
    r"|(?P<mdlink>\[[^\]\n]+\]\([^)\n]+\))"
    r"|(?P<url>https?://\S+)"
)

_CAPTION_RE = re.compile(r'(caption\s*=\s*)"([^"]*)"')
_MDLINK_RE = re.compile(r'\[([^\]\n]+)\]\(([^)\n]+)\)')
_PARA_SPLIT = re.compile(r"(\n{2,})")


@dataclass
class Builder:
    """Accumulates body parts, deferring translatable strings to a flat list."""
    parts: list[tuple[str, object]] = field(default_factory=list)
    translatables: list[str] = field(default_factory=list)

    def lit(self, s: str) -> None:
        if s:
            self.parts.append(("lit", s))

    def tr(self, s: str) -> None:
        # Bypass empty / whitespace-only strings — never worth a round trip.
        if not s.strip():
            self.lit(s)
            return
        # Split prose chunks on blank-line paragraph breaks so each LLM call
        # sees a coherent unit and a single failure doesn't poison the file.
        for piece in _PARA_SPLIT.split(s):
            if not piece:
                continue
            if not piece.strip():
                self.lit(piece)
            else:
                self.parts.append(("tr", len(self.translatables)))
                self.translatables.append(piece)

    def reassemble(self, translated: list[str]) -> str:
        out: list[str] = []
        for kind, val in self.parts:
            if kind == "lit":
                out.append(val)  # type: ignore[arg-type]
            else:
                out.append(translated[val])  # type: ignore[index]
        return "".join(out)


def segment_body(body: str) -> Builder:
    b = Builder()
    last = 0
    for m in _TOKEN_RE.finditer(body):
        if m.start() > last:
            b.tr(body[last:m.start()])
        kind = m.lastgroup
        chunk = m.group(0)
        if kind == "shortcode":
            _emit_shortcode(b, chunk)
        elif kind == "mdlink":
            _emit_mdlink(b, chunk)
        else:
            b.lit(chunk)
        last = m.end()
    if last < len(body):
        b.tr(body[last:])
    return b


def _emit_mdlink(b: Builder, link: str) -> None:
    """Emit a markdown link, translating only the visible text."""
    m = _MDLINK_RE.fullmatch(link)
    if not m:
        b.lit(link)
        return
    text, url = m.group(1), m.group(2)
    b.lit("[")
    b.tr(text)
    b.lit(f"]({url})")


def _emit_shortcode(b: Builder, sc: str) -> None:
    """Emit a Hugo shortcode, peeling out caption="..." values as translatables."""
    cursor = 0
    for cap in _CAPTION_RE.finditer(sc):
        # Literal: text up to and including the caption= and opening quote.
        # cap.group(1) is the `caption=` (with optional whitespace) prefix.
        prefix_end = cap.start() + len(cap.group(1)) + 1   # +1 for opening "
        b.lit(sc[cursor:prefix_end])
        b.tr(cap.group(2))
        cursor = prefix_end + len(cap.group(2))            # land on the closing "
    b.lit(sc[cursor:])


# --- LLM client -----------------------------------------------------------

def _build_system_prompt(target_lang: str) -> str:
    target_name = LANG_NAMES.get(target_lang, target_lang)
    return (
        f"You are a translator for a personal blog about cycling, hiking, and tinkering. "
        f"The user sends a JSON object {{\"texts\": [...]}} containing N strings (Chinese, English, "
        f"or mixed; auto-detect per item). Translate each item to natural, fluent {target_name}. "
        f"Preserve all markdown formatting EXACTLY: headings (# ## ###), lists (- *), "
        f"bold (**text**), italic (*text*), inline code (`text`), links. "
        f"Keep numbers, dates, times, and proper nouns. If an item is already in {target_name}, "
        f"return it unchanged. "
        f"Reply with ONLY a JSON object of the form {{\"translations\": [...]}} containing exactly N "
        f"translated strings in the same order. No prose, no code fences, no commentary."
    )

_BATCH_MAX_ITEMS = 30
_BATCH_MAX_CHARS = 8000

# Notice prepended to every translated body. Per-language; falls back to English.
AI_NOTICES = {
    "en": "> _Note: this article was machine-translated and may contain inaccuracies. Please refer to the original for definitive meaning._",
    "zh-Hant": "> _注意：本文由 AI 自動翻譯，可能有誤譯，請以原文為準。_",
}


def _notice_for(target_lang: str) -> str:
    return AI_NOTICES.get(target_lang, AI_NOTICES["en"])


def _upsert_ai_translated_flag(fm_text: str, delim: str) -> str:
    line = "ai_translated = true" if delim == "+++" else "ai_translated: true"
    pat = re.compile(r"^ai_translated\s*[:=].*$", re.MULTILINE)
    if pat.search(fm_text):
        return pat.sub(line, fm_text)
    return fm_text.rstrip() + "\n" + line + "\n"


def _format_batch_user(texts: list[str]) -> str:
    return json.dumps({"texts": texts}, ensure_ascii=False)


def _parse_batch_response(raw: str, expected: int) -> list[str]:
    s = _clean_llm_output(raw)
    # Locate the outermost JSON object even if model added stray prose.
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"no JSON object found in response: {s[:200]!r}")
    obj = json.loads(s[start:end + 1])
    arr = obj.get("translations")
    if not isinstance(arr, list):
        raise ValueError(f"missing 'translations' array: {obj!r}")
    if len(arr) != expected:
        raise ValueError(f"expected {expected} translations, got {len(arr)}")
    return [str(x) for x in arr]


def _chunk_texts(texts: list[str]) -> list[list[str]]:
    chunks: list[list[str]] = []
    cur: list[str] = []
    cur_chars = 0
    for t in texts:
        if cur and (len(cur) >= _BATCH_MAX_ITEMS or cur_chars + len(t) > _BATCH_MAX_CHARS):
            chunks.append(cur)
            cur, cur_chars = [], 0
        cur.append(t)
        cur_chars += len(t)
    if cur:
        chunks.append(cur)
    return chunks


def translate_all(client, texts: list[str]) -> list[str]:
    """Translate a list of strings via batched LLM calls. Falls back to size-1 batches on failure."""
    out: list[str] = []
    chunks = _chunk_texts(texts)
    for ci, chunk in enumerate(chunks, 1):
        try:
            translated = client.translate_batch(chunk)
        except Exception as e:
            print(f"  batch {ci}/{len(chunks)} failed ({e}); retrying items individually", flush=True)
            translated = []
            for t in chunk:
                try:
                    translated.append(client.translate_batch([t])[0])
                except Exception as ee:
                    print(f"    item failed ({ee}); keeping source", flush=True)
                    translated.append(t)
        out.extend(translated)
        print(f"  {len(out)}/{len(texts)}", flush=True)
    return out


class RateLimiter:
    """Sliding-window limiter: at most `rpm` calls per 60s. rpm=0 disables."""

    def __init__(self, rpm: int) -> None:
        self.rpm = max(0, rpm)
        self.window = 60.0
        self._calls: deque[float] = deque()

    def wait(self) -> None:
        if self.rpm == 0:
            return
        now = time.monotonic()
        while self._calls and now - self._calls[0] >= self.window:
            self._calls.popleft()
        if len(self._calls) >= self.rpm:
            sleep_for = self.window - (now - self._calls[0]) + 0.05
            if sleep_for > 0:
                print(f"  rate limit ({self.rpm}/min): sleeping {sleep_for:.1f}s", flush=True)
                time.sleep(sleep_for)
            now = time.monotonic()
            while self._calls and now - self._calls[0] >= self.window:
                self._calls.popleft()
        self._calls.append(time.monotonic())


def _resolve_rpm(default: int) -> int:
    raw = os.environ.get("LLM_RPM")
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        sys.exit(f"LLM_RPM must be an integer, got {raw!r}")


class OpenAIClient:
    """Talks to any OpenAI-compatible chat-completions endpoint (LM Studio, Ollama, vLLM, ...)."""

    def __init__(self, target_lang: str) -> None:
        from openai import OpenAI  # local import — only needed for this provider

        base_url = os.environ.get("LLM_BASE_URL")
        if not base_url:
            sys.exit("LLM_BASE_URL must be set for openai provider")
        model = os.environ.get("LLM_MODEL")
        if not model:
            sys.exit("LLM_MODEL must be set for openai provider")
        api_key = os.environ.get("LLM_API_KEY", "local")
        self._model = model
        self._client = OpenAI(base_url=base_url, api_key=api_key)
        self._limiter = RateLimiter(_resolve_rpm(default=0))
        self._system = _build_system_prompt(target_lang)

    def translate_batch(self, texts: list[str]) -> list[str]:
        if not texts:
            return []
        self._limiter.wait()
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": self._system},
                {"role": "user", "content": _format_batch_user(texts)},
            ],
            temperature=0.2,
        )
        return _parse_batch_response(resp.choices[0].message.content or "", expected=len(texts))


class GeminiClient:
    """Talks to Google's generativelanguage REST endpoint directly via stdlib HTTP."""

    def __init__(self, target_lang: str) -> None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            sys.exit("GEMINI_API_KEY must be set for gemini provider")
        model = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
        self._api_key = api_key
        self._endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        )
        self._limiter = RateLimiter(_resolve_rpm(default=5))
        self._system = _build_system_prompt(target_lang)

    def translate_batch(self, texts: list[str]) -> list[str]:
        if not texts:
            return []
        self._limiter.wait()
        payload = json.dumps({
            "systemInstruction": {"parts": [{"text": self._system}]},
            "contents": [{"parts": [{"text": _format_batch_user(texts)}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }).encode("utf-8")
        req = urllib.request.Request(
            self._endpoint,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-goog-api-key": self._api_key,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Gemini HTTP {e.code}: {body}") from e
        candidates = data.get("candidates") or []
        if not candidates:
            raise RuntimeError(f"Gemini returned no candidates: {data}")
        parts = candidates[0].get("content", {}).get("parts", [])
        out = "".join(p.get("text", "") for p in parts)
        if not out:
            raise RuntimeError(f"Gemini returned empty text: {data}")
        return _parse_batch_response(out, expected=len(texts))


def _make_client(target_lang: str):
    provider = os.environ.get("LLM_PROVIDER", "").strip().lower()
    if not provider:
        if os.environ.get("GEMINI_API_KEY"):
            provider = "gemini"
        elif os.environ.get("LLM_BASE_URL"):
            provider = "openai"
        else:
            sys.exit(
                "no provider configured: set LLM_BASE_URL (openai-compat) or "
                "GEMINI_API_KEY (gemini), or set LLM_PROVIDER explicitly"
            )
    if provider == "openai":
        return OpenAIClient(target_lang)
    if provider == "gemini":
        return GeminiClient(target_lang)
    sys.exit(f"unknown LLM_PROVIDER: {provider!r} (expected 'openai' or 'gemini')")


def _clean_llm_output(s: str) -> str:
    s = s.strip()
    # Strip a single wrapping pair of quotes that the model sometimes adds.
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        inner = s[1:-1]
        if s[0] not in inner:
            s = inner
    # Strip ``` code fences if the model wrapped output as a code block.
    if s.startswith("```"):
        lines = s.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    return s


# --- Per-file driver ------------------------------------------------------

def _hash_source(title: str, body: str) -> str:
    h = hashlib.sha256()
    h.update(title.encode("utf-8"))
    h.update(b"\n--BODY--\n")
    h.update(body.encode("utf-8"))
    return "sha256:" + h.hexdigest()[:32]


def _split_lang_suffix(stem: str) -> tuple[str, str | None]:
    """Strip a known language suffix from a filename stem; return (base, lang | None)."""
    for lang in KNOWN_LANGS:
        suffix = f".{lang}"
        if stem.endswith(suffix):
            return stem[: -len(suffix)], lang
    return stem, None


def _translation_path(src: Path, target_lang: str) -> Path:
    base, _ = _split_lang_suffix(src.stem)
    return src.parent / f"{base}.{target_lang}.md"


def _has_target_suffix(p: Path, target_lang: str) -> bool:
    _, lang = _split_lang_suffix(p.stem)
    return lang == target_lang


def translate_file(src: Path, target_lang: str, *, dry_run: bool = False, force: bool = False) -> None:
    rel = src.relative_to(REPO_ROOT)
    out_path = _translation_path(src, target_lang)
    if out_path.resolve() == src.resolve():
        print(f"skip (source already in target lang): {rel}")
        return

    raw = src.read_text(encoding="utf-8")
    fm = split_frontmatter(raw)
    title = get_title(fm.text) or ""
    body = fm.body
    source_hash = _hash_source(title, body)

    if out_path.exists() and not force:
        existing = out_path.read_text(encoding="utf-8")
        try:
            existing_hash = get_source_hash(split_frontmatter(existing).text)
        except ValueError:
            existing_hash = None
        if existing_hash == source_hash:
            print(f"skip (cached): {rel}")
            return

    builder = segment_body(body)
    n_segments = len(builder.translatables)

    if dry_run:
        print(f"\n=== {rel} — {n_segments} segments ===")
        for i, s in enumerate(builder.translatables):
            preview = s[:120].replace("\n", " ⏎ ")
            print(f"[{i:>3}] {preview!r}")
        return

    client = _make_client(target_lang)
    # Honour a hand-crafted target-language title if present (e.g. title_en, title_zh_hant).
    title_override_field = f"title_{target_lang.replace('-', '_').lower()}"
    title_override = get_field(fm.text, title_override_field)

    # Build a single request: optional title + body segments. The first item is
    # the title only when it needs translating; otherwise it's omitted.
    needs_title = bool(title) and not title_override
    inputs = ([title] if needs_title else []) + builder.translatables
    print(f"translating {rel} → {target_lang} ({len(inputs)} segments, {len(_chunk_texts(inputs))} batch(es)) …", flush=True)
    translated_all = translate_all(client, inputs)
    if needs_title:
        title_target = translated_all[0]
        translated_body = translated_all[1:]
    else:
        title_target = title_override or title
        translated_body = translated_all
    body_target = _notice_for(target_lang) + "\n\n" + builder.reassemble(translated_body)

    new_fm = replace_title(fm.text, title_target or title)
    new_fm = upsert_source_hash(new_fm, fm.delim, source_hash)
    new_fm = _upsert_ai_translated_flag(new_fm, fm.delim)
    out = f"{fm.delim}{new_fm}{fm.delim}\n\n{body_target}"
    out_path.write_text(out, encoding="utf-8")
    print(f"wrote {out_path.relative_to(REPO_ROOT)}")


# --- CLI ------------------------------------------------------------------

def _iter_sources(paths: list[str], target_lang: str) -> list[Path]:
    """Resolve source paths. When walking, skip files already in the target language."""
    if paths:
        result = [Path(p).resolve() for p in paths]
    else:
        result = [
            p for p in CONTENT_ROOT.rglob("*.md")
            if not _has_target_suffix(p, target_lang)
        ]
    return sorted(p for p in result if p.is_file())


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paths", nargs="*", help="markdown source paths (default: all)")
    ap.add_argument(
        "--target", "-t",
        default=os.environ.get("TARGET", "en"),
        help=f"target language code (default: $TARGET or 'en'). Known: {', '.join(KNOWN_LANGS)}",
    )
    ap.add_argument("--dry-run", action="store_true", help="show segments without calling LLM")
    ap.add_argument("--force", action="store_true", help="ignore cached source_hash")
    args = ap.parse_args(argv)

    if args.target not in KNOWN_LANGS:
        print(
            f"warning: target {args.target!r} not in KNOWN_LANGS={KNOWN_LANGS}; "
            f"output filename will use it as-is",
            file=sys.stderr,
        )

    sources = _iter_sources(args.paths, args.target)
    if not sources:
        print("no markdown sources found", file=sys.stderr)
        return 1

    for src in sources:
        try:
            translate_file(src, args.target, dry_run=args.dry_run, force=args.force)
        except Exception as e:
            print(f"error: {src}: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
