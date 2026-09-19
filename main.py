import os
import itertools
import concurrent.futures

from hls_playlist import (
    HLSMasterPlaylist, HLSMediaPlaylist, 
    read_curl_command, combine_segments,
    scrape, scrape_segment_with_multiprocessing,
)
from pathlib import Path


# create a temporary directory to store all the segments
TEMPDIR=Path(__file__).parent / ".temp"
TEMPDIR.mkdir(exist_ok=True)


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
        resp = scrape(url=url, headers=headers)
        if (resp != None):
            break
    
    # if none found
    if (resp == None):
        print(f"Could not find the master playlist")
        return
    
    # parse the output and get the possible resolutions
    print("Found its master playlist")
    m3u8 = HLSMasterPlaylist(text=resp)
    for i, mv in enumerate(m3u8.media_variants):
        print(f"{i + 1}. Resolution Found: {mv.resolution}")
        
    # getting the actual m3u8 based on the resolution
    resolution_picked: int = 0
    try:
        resolution_picked = input(f"Which resolution would you like to download ({1} - {len(m3u8.media_variants)})? ")
        resolution_picked = int(resolution_picked)
    except ValueError:
        print("Invalid input! Aborted!")
        return

    # get the url based on the resolution picked
    url = base_url + "/" + m3u8.media_variants[resolution_picked - 1].uri
    print(f"URL:{url}")
    resp = scrape(url=url, headers=headers)
    
    # if none found
    if (resp == None):
        print(f"Could not find the master playlist")
        return
    
    media_m3u8 = HLSMediaPlaylist(text=resp)
    
    # get the init
    resp = scrape(url=media_m3u8.uri, headers=headers, decode=False)
    if (resp != None):
        import re
        from re import Pattern
                
        filename_re: Pattern = re.compile(r'https://.*/(.*.mp4).*')
        filename: list[str] = filename_re.findall(media_m3u8.uri)
        
        print(filename)
        if (len(filename) > 0):
            file: Path = TEMPDIR / filename[0]
            file.write_bytes(resp)
            
    # using multiprocessing
    with concurrent.futures.ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        executor.map(
            scrape_segment_with_multiprocessing, # the function
            media_m3u8.segments, # the segments
            itertools.repeat(headers), # constant 1: header
            itertools.repeat(TEMPDIR), # constant 2: temp folder
        )
    
    # combine the segments
    combine_segments(temp_dir=TEMPDIR)   


if (__name__ == "__main__"):
    main()
