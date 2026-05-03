#!/usr/bin/env python3
"""Sync cycling-videos markdown files from channel.db + YouTube playlist.

Creates markdown files for playlist videos not yet on the site and updates
view counts in existing files.
"""

import pickle
import re
import sqlite3
import sys
from pathlib import Path

# ── paths ──────────────────────────────────────────────────────────────────
import os

CHANNEL_MANAGER = Path(os.environ["CHANNEL_MANAGER_DIR"])
DB_PATH         = Path(os.getenv("CHANNEL_DB", str(CHANNEL_MANAGER / "channel.db")))
CONTENT_DIR     = Path(__file__).parent.parent / "content" / "cycling-videos"
PLAYLIST_ID     = "PLBw7mmClezKtxx-kXIOuT9yokAsqYNjI4"

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

# ── auth ───────────────────────────────────────────────────────────────────
def _get_credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    # prefer .oauth_token.json, fall back to token.pickle
    json_path   = CHANNEL_MANAGER / ".oauth_token.json"
    pickle_path = CHANNEL_MANAGER / "token.pickle"

    creds = None
    if json_path.exists():
        creds = Credentials.from_authorized_user_file(json_path, SCOPES)
    elif pickle_path.exists():
        with pickle_path.open("rb") as f:
            creds = pickle.load(f)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        json_path.write_text(creds.to_json())

    if not creds or not creds.valid:
        sys.exit("No valid credentials found. Run auth in channel-manager first.")

    return creds


def _youtube():
    from googleapiclient.discovery import build
    return build("youtube", "v3", credentials=_get_credentials())


# ── YouTube helpers ────────────────────────────────────────────────────────
def fetch_playlist_ids(yt, playlist_id: str) -> list[str]:
    ids, page_token = [], None
    while True:
        resp = yt.playlistItems().list(
            part="contentDetails",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=page_token,
        ).execute()
        for item in resp["items"]:
            ids.append(item["contentDetails"]["videoId"])
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return ids


# ── formatting helpers ─────────────────────────────────────────────────────
def fmt_duration(secs: int | None) -> str:
    if not secs:
        return ""
    h, m = divmod(secs // 60, 60)
    return f"{h}h {m}m" if h else f"{m}m"


def slugify(title: str, date_prefix: str) -> str:
    s = re.sub(r"^\d{8}\s*", "", title)                          # strip leading date
    s = re.sub(r"\[\s*(4K|2K|120fps|HD)\s*\]", "", s, flags=re.IGNORECASE)
    s = re.sub(r"[\[\]]", "", s)                                   # remove brackets
    s = re.sub(r"[\s_]+", "-", s.strip())
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return f"{date_prefix}-{s}"


def make_markdown(video_id, title, date_str, duration_sec, view_count) -> str:
    date     = (date_str or "")[:10]
    duration = fmt_duration(duration_sec)
    views    = view_count or 0
    return (
        "---\n"
        f'title: "{title}"\n'
        f"date: {date}\n"
        "draft: false\n"
        'tags: ["cycling-videos"]\n'
        f'youtube_id: "{video_id}"\n'
        f'duration: "{duration}"\n'
        f"views: {views}\n"
        "---\n"
        "\n"
        f"{{{{< youtube {video_id} >}}}}\n"
        "\n"
        f"**Duration:** {duration}  \n"
        f"**Views:** {views}  \n"
        f"**Published:** {date}\n"
    )


# ── existing markdown index ────────────────────────────────────────────────
def existing_by_id() -> dict[str, Path]:
    result = {}
    for md in CONTENT_DIR.glob("*.md"):
        m = re.search(r'^youtube_id:\s*["\']?(\S+?)["\']?\s*$', md.read_text(), re.MULTILINE)
        if m:
            result[m.group(1)] = md
    return result


# ── main ───────────────────────────────────────────────────────────────────
def main():
    con = sqlite3.connect(DB_PATH)
    db = {
        row[0]: row
        for row in con.execute(
            "SELECT video_id, title, published_at, duration_sec, view_count FROM video"
        )
    }
    con.close()

    print("Fetching playlist …")
    yt = _youtube()
    playlist_ids = fetch_playlist_ids(yt, PLAYLIST_ID)
    print(f"  {len(playlist_ids)} videos in playlist\n")

    existing = existing_by_id()
    created = updated = skipped = missing_db = 0

    for vid in playlist_ids:
        if vid not in db:
            print(f"  not in db   {vid}")
            missing_db += 1
            continue

        video_id, title, published_at, duration_sec, view_count = db[vid]
        date_prefix = (published_at or "")[:10].replace("-", "")

        if vid in existing:
            md   = existing[vid]
            text = md.read_text()
            new  = re.sub(r'^views:\s*\d+', f'views: {view_count or 0}', text, flags=re.MULTILINE)
            new  = re.sub(r'\*\*Views:\*\*\s*\d+', f'**Views:** {view_count or 0}', new)
            if new != text:
                md.write_text(new)
                print(f"  updated     {md.name}  → {view_count} views")
                updated += 1
            else:
                skipped += 1
        else:
            slug = slugify(title, date_prefix)
            path = CONTENT_DIR / f"{slug}.md"
            path.write_text(make_markdown(video_id, title, published_at, duration_sec, view_count))
            print(f"  created     {path.name}")
            created += 1

    print(f"\n{created} created, {updated} updated, {skipped} unchanged, {missing_db} not in db")


if __name__ == "__main__":
    main()
