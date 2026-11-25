"""eslarma.uz bot, stage 2: download queued reels and store them as private release assets."""
import json
import os
import subprocess
import urllib.request

import bot

VIDEO_DIR = "videos"
RELEASE_TAG = "videos"
MAX_ATTEMPTS = 3


def sh(*args):
    return subprocess.run(args, capture_output=True, text=True, timeout=600)


def ensure_release():
    if sh("gh", "release", "view", RELEASE_TAG).returncode != 0:
        sh("gh", "release", "create", RELEASE_TAG, "--title", "videos", "--notes", "Source videos")


def download_link(url, out):
    cmd = ["yt-dlp", "--no-playlist", "--no-progress", "-f", "best[ext=mp4]/best",
           "--merge-output-format", "mp4", "-o", out]
    if os.path.exists("cookies.txt"):
        cmd += ["--cookies", "cookies.txt"]
    res = sh(*cmd, url)
    if res.returncode != 0 or not os.path.exists(out):
        raise RuntimeError((res.stderr or res.stdout).strip().splitlines()[-1:] or ["unknown error"])


def download_file(file_id, out):
    info = bot.call("getFile", file_id=file_id)
    url = f"https://api.telegram.org/file/bot{bot.TOKEN}/{info['file_path']}"
    urllib.request.urlretrieve(url, out)


def main():
    state = bot.load(bot.STATE_PATH, {})
    owner = state.get("owner_chat_id")
    queue = bot.load(bot.QUEUE_PATH, [])
    todo = [it for it in queue if it["status"] in ("new", "retry")]
    if not todo:
        print("nothing to download")
        return
    os.makedirs(VIDEO_DIR, exist_ok=True)

    for idx, item in enumerate(queue):
        if item not in todo:
            continue
        name = f"src_{idx + 1:04d}.mp4"
        out = os.path.join(VIDEO_DIR, name)
        item["attempts"] = item.get("attempts", 0) + 1
        try:
            if item["type"] == "link":
                download_link(item["url"], out)
            else:
                download_file(item["file_id"], out)
            item["status"] = "downloaded"
            item["video_asset"] = name
            item["video_bytes"] = os.path.getsize(out)
            item.pop("error", None)
            if owner:
                bot.reply(owner, f"Скачал ролик №{idx + 1} ✅ Дальше он пойдёт в обработку.")
        except Exception as exc:  # noqa: BLE001
            item["error"] = str(exc)[:300]
            if item["attempts"] >= MAX_ATTEMPTS:
                item["status"] = "download_failed"
                if owner:
                    where = item.get("url", "присланный файл")
                    bot.reply(owner, "Не получилось скачать ролик:\n"
                                     f"{where}\n\nИнстаграм не отдаёт видео. Скачайте его через "
                                     "любой бот-загрузчик и перешлите файл сюда — я возьму его.")
            else:
                item["status"] = "retry"
        bot.save(bot.QUEUE_PATH, queue)


if __name__ == "__main__":
    main()
