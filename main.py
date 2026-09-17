import urllib.request

from hls_playlist import HLSMasterPlaylist, read_curl_command
from pathlib import Path


# create a temporary directory to store all the segments
TEMP_DIR=Path(__file__).parent / ".temp"
TEMP_DIR.mkdir(exist_ok=True)


def main():
    # get the headers and the base url
    curl_cmd_file = Path(__file__).parent / "curl.cmd"
    text = curl_cmd_file.read_text(encoding="utf-8")
    headers, base_url = read_curl_command(text)

    # get the master playlist
    possible_master_names = [
        
        # most common / generic (first try)
        "master.m3u8",
        "index.m3u8",
        "playlist.m3u8",
        "main.m3u8",
        "manifest.m3u8",
        "stream.m3u8",
        "hls.m3u8",
        "video.m3u8",
        "live.m3u8",
        "vod.m3u8",
        "all.m3u8",
        "default.m3u8",
        "variants.m3u8",
        "media.m3u8",
        
        # compount / descriptive
        "master_playlist.m3u8",
        "playlist_index.m3u8",
        "master_index.m3u8",
        "index_playlist.m3u8",
        "playlist_master.m3u8",
        "master_playlist_index.m3u8",
        "stream_index.m3u8",
        "hls_playlist.m3u8",
        "hls_master.m3u8",
    ]
    resp = None
    for possible_master_name in possible_master_names:
        print(f"Retrying with '{possible_master_name}'")
        url = base_url + "/" + possible_master_name
        req = urllib.request.Request(url=url, headers=headers)
        with urllib.request.urlopen(req) as response:
            status = response.status
            if (status == 200):
                resp = response.read().decode("utf-8")
                break
    
    # if none found
    if (resp == None):
        print(f"Could not find the master playlist")
        return
    
    # parse the output and get the possible resolutions
    m3u8 = HLSMasterPlaylist(text=resp)
    for i, mv in enumerate(m3u8.media_variants):
        print(f"{i + 1}. {mv.bandwidth}, {mv.resolution}, {mv.uri}")

    # after getting the user input, download all the segments using multiprocessing


if (__name__ == "__main__"):
    main()
