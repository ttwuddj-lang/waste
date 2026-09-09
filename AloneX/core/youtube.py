# ALONE-CODER
import os
import re
import random
import aiohttp
from py_yt import VideosSearch, Playlist
from AloneX import logger, config
from AloneX.helpers import Track, utils

API_URL = os.environ.get("SHRUTI_API_URL", "https://api.shrutibots.site")
API_KEY = os.environ.get("SHRUTI_API_KEY", "ShrutiBotsnUp5eKvUKskT9x4e45EF")
DOWNLOAD_DIR = "downloads"


async def download_song(link: str) -> str:
    video_id = link.split("v=")[-1].split("&")[0] if "v=" in link else link
    if not video_id or len(video_id) < 3:
        return None
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.mp3")
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        return file_path
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{API_URL}/download",
                params={"url": video_id, "type": "audio", "api_key": API_KEY},
                timeout=aiohttp.ClientTimeout(total=300),
            ) as resp:
                if resp.status != 200:
                    return None
                with open(file_path, "wb") as f:
                    async for chunk in resp.content.iter_chunked(131072):
                        f.write(chunk)
        return file_path if os.path.exists(file_path) and os.path.getsize(file_path) > 0 else None
    except Exception:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
        return None


async def download_video(link: str) -> str:
    video_id = link.split("v=")[-1].split("&")[0] if "v=" in link else link
    if not video_id or len(video_id) < 3:
        return None
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.mp4")
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        return file_path
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{API_URL}/download",
                params={"url": video_id, "type": "video", "api_key": API_KEY},
                timeout=aiohttp.ClientTimeout(total=600),
            ) as resp:
                if resp.status != 200:
                    return None
                with open(file_path, "wb") as f:
                    async for chunk in resp.content.iter_chunked(131072):
                        f.write(chunk)
        return file_path if os.path.exists(file_path) and os.path.getsize(file_path) > 0 else None
    except Exception:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
        return None


class YouTube:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = re.compile(
            r"(https?://)?(www\.|m\.|music\.)?"
            r"(youtube\.com/(watch\?v=|shorts/|playlist\?list=)|youtu\.be/)"
            r"([A-Za-z0-9_-]{11}|PL[A-Za-z0-9_-]+)([&?][^\s]*)?"
        )
        self.cookie_dir = "AloneX/cookies"

    def get_cookies(self):
        if not os.path.exists(self.cookie_dir):
            return None
        files = [f for f in os.listdir(self.cookie_dir) if f.endswith(".txt")]
        return os.path.join(self.cookie_dir, random.choice(files)) if files else None

    async def save_cookies(self, urls: list[str]) -> None:
        logger.info("Saving cookies from urls...")
        os.makedirs(self.cookie_dir, exist_ok=True)
        async with aiohttp.ClientSession() as session:
            for i, url in enumerate(urls):
                path = f"{self.cookie_dir}/cookie_{i}.txt"
                link = "https://batbin.me/api/v2/paste/" + url.split("/")[-1]
                async with session.get(link) as resp:
                    resp.raise_for_status()
                    with open(path, "wb") as fw:
                        fw.write(await resp.read())
        logger.info("Cookies saved.")

    def valid(self, url: str) -> bool:
        return bool(re.match(self.regex, url))

    async def search(self, query: str, m_id: int, video: bool = False) -> Track | None:
        try:
            result = await VideosSearch(query, limit=1).next()
            if result and result["result"]:
                data = result["result"][0]
                return Track(
                    id=data.get("id"),
                    channel_name=data.get("channel", {}).get("name"),
                    duration=data.get("duration"),
                    duration_sec=utils.to_seconds(data.get("duration")) if data.get("duration") else 0,
                    message_id=m_id,
                    title=(data.get("title") or "Unknown")[:25],
                    thumbnail=data.get("thumbnails", [{}])[-1].get("url", "").split("?")[0],
                    url=data.get("link"),
                    view_count=data.get("viewCount", {}).get("short"),
                    video=video,
                )
        except Exception as e:
            logger.error(f"Search error: {e}")
        return None

    async def related(self, current: Track, m_id: int, video: bool = False) -> Track | None:
        """Find a different track for automatic queue playback."""
        queries = [
            f"songs similar to {current.title}",
            f"more songs like {current.title}",
        ]
        for query in queries:
            try:
                result = await VideosSearch(query, limit=8).next()
                items = result.get("result", []) if result else []
                random.shuffle(items)
                for data in items:
                    vid = data.get("id")
                    if not vid or vid == current.id:
                        continue
                    duration = data.get("duration")
                    duration_sec = utils.to_seconds(duration) if duration else 0
                    if not duration_sec or duration_sec > config.DURATION_LIMIT:
                        continue
                    return Track(
                        id=vid,
                        channel_name=data.get("channel", {}).get("name"),
                        duration=duration,
                        duration_sec=duration_sec,
                        message_id=m_id,
                        title=(data.get("title") or "Unknown")[:25],
                        thumbnail=data.get("thumbnails", [{}])[-1].get("url", "").split("?")[0],
                        url=data.get("link"),
                        view_count=data.get("viewCount", {}).get("short"),
                        video=video,
                    )
            except Exception as e:
                logger.error(f"Autoplay search error: {e}")
        return None

    async def playlist(self, limit: int, user: str, url: str, video: bool) -> list[Track]:
        tracks = []
        try:
            plist = await Playlist.get(url)
            for data in plist.get("videos", [])[:limit]:
                track = Track(
                    id=data.get("id"),
                    channel_name=data.get("channel", {}).get("name", ""),
                    duration=data.get("duration"),
                    duration_sec=utils.to_seconds(data.get("duration")) if data.get("duration") else 0,
                    title=(data.get("title") or "Unknown")[:25],
                    thumbnail=data.get("thumbnails", [{}])[-1].get("url", "").split("?")[0],
                    url=data.get("link").split("&list=")[0],
                    user=user,
                    view_count="",
                    video=video,
                )
                tracks.append(track)
        except Exception as e:
            logger.error(f"Playlist error: {e}")
        return tracks

    async def download(self, video_id: str, video: bool = False) -> str | None:
        if not video_id or len(video_id) < 3:
            return None
        return await download_video(video_id) if video else await download_song(video_id)
