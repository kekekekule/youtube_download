import sys
import argparse
import pytube
import re
import json

from pathlib import Path
from http.client import IncompleteRead
from urllib.error import URLError

from pytube.cli import display_progress_bar

from helpers import TextColors


YOUTUBE_STREAM_AUDIO = "140"

PLAYLIST_URL_FORMAT = "https://www.youtube.com/playlist?list={}"


def on_progress(stream, chunk, bytes_remaining):
    print(f"{TextColors.BOLD}\t>>> Remaining {bytes_remaining} bytes...{TextColors.ENDC}")


def download(filestream):
    def _configure_ssl():
        import ssl

        ssl._create_default_https_context = ssl._create_unverified_context

    def _perform_dl(stream, path_for_saved):
        stream.on_progress = on_progress
        stream.download(path_for_saved)

    _configure_ssl()

    filestream.seek(0)

    config = json.loads(filestream.read())

    for channel_name, plist_ids in config.items():
        for plst in plist_ids:
            playlist_id = plst["id"]
            playlist_title = plst["title"]
            playlist = pytube.Playlist(PLAYLIST_URL_FORMAT.format(playlist_id))
            playlist._video_regex = re.compile(r"\"url\":\"(/watch\?v=[\w-]*)")
            title = playlist_title.replace("/", "-", 100).replace("\\", "-", 100)
            print(
                f"{TextColors.OKCYAN}--- Download playlist {title} ---{TextColors.ENDC}"
            )

            Path(f"./{channel_name}/{playlist_title}").mkdir(
                parents=True, exist_ok=True
            )

            path_for_saved = f"./{channel_name}/{title}"

            print(
                f"{TextColors.OKCYAN}Number of videos in playlist: {len(playlist.video_urls)}{TextColors.ENDC}"
            )

            count_downloaded = 0
            count_in_playlist = len(playlist.video_urls)
            for video in playlist.videos:
                tries = 0
                while tries < 3:
                    try:
                        video_stream = (
                            video.streams.filter(
                                type="video", progressive=True, file_extension="mp4"
                            )
                            .order_by("resolution")
                            .desc()
                            .first()
                        )

                        _perform_dl(video_stream, path_for_saved)
                        break
                    except (IncompleteRead, URLError):
                        print(f"{TextColors.FAIL}Failed. Retrying...{TextColors.ENDC}\r")
                        tries += 1
                else:
                    print(
                        f"{TextColors.WARNING}Could not download afrer {tries} attempts. Skipping.\r"
                    )

                count_downloaded += 1
                print(
                    f"{TextColors.OKGREEN}Processed {count_downloaded}/{count_in_playlist} videos{TextColors.ENDC}\r"
                )


parser = argparse.ArgumentParser(description="Process cmdline arguments")

parser.add_argument(
    "--input",
    dest="input",
    type=argparse.FileType("r"),
    default=sys.stdin,
    help="input stream (default stdin)",
)

args = parser.parse_args()

if __name__ == "__main__":
    ok = False
    while not ok:
        try:
            download(filestream=args.input)
            ok = True
        except URLError:
            print(
                f"{TextColors.WARNING}!!! Lost connection. Retrying...{TextColors.ENDC}"
            )
