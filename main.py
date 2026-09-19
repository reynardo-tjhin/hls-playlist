import itertools
import concurrent.futures

from hls_playlist import (
    HLSMasterPlaylist, HLSMediaPlaylist, 
    read_curl_command, combine_segments,
    scrape, scrape_segment_with_multiprocessing,
)
from pathlib import Path
from tqdm import tqdm


NUM_WORKERS=4

# create a temporary directory to store all the segments
TEMPDIR=Path(__file__).parent / ".temp"
TEMPDIR.mkdir(exist_ok=True)

# get the headers and the base url from hardcoded "curl.cmd" file
CURL_CMD_FILE = Path(__file__).parent / "curl.cmd"
text = CURL_CMD_FILE.read_text(encoding="utf-8")
HEADERS, MASTER_BASE_URL = read_curl_command(text)

# get all the possible master candidates
MASTER_CANDIDATES_FILE=Path(__file__).parent / "master_candidates.txt"
temp = MASTER_CANDIDATES_FILE.read_text(encoding="utf-8").splitlines()
MASTER_CANDIDATE_NAMES = [line for line in temp if not line.startswith("#") and line != ""]


def main():
    # Step 1: get the master playlist
    resp = None
    for possible_master_name in MASTER_CANDIDATE_NAMES:
        print(f"Retrying with '{possible_master_name}'")
        url = MASTER_BASE_URL + "/" + possible_master_name
        resp = scrape(url=url, headers=HEADERS)
        if (resp != None):
            break
    
    # Step 1.1: could not find the master playlist -> reject any retries
    if (resp == None):
        print("ERROR: Could not find the master playlist")
        return
    
    # Step 2: parse the output and get the possible resolutions
    print("Found its master playlist")
    m3u8 = HLSMasterPlaylist(text=resp)
    for i, mv in enumerate(m3u8.media_variants):
        print(f"{i + 1}. Resolution Found: {mv.resolution}")
        
    # Step 3: asks for user input: getting the actual m3u8 based on the resolution
    resolution_picked: int = 0
    try:
        resolution_picked = input(f"Which resolution would you like to download ({1} - {len(m3u8.media_variants)})? ")
        resolution_picked = int(resolution_picked)
    except ValueError:
        print("Invalid input! Aborted!")
        return

    # get the url based on the resolution picked
    url = MASTER_BASE_URL + "/" + m3u8.media_variants[resolution_picked - 1].uri
    print(f"URL:{url}")
    resp = scrape(url=url, headers=HEADERS)
    
    # if none found
    if (resp == None):
        print(f"Could not find the master playlist")
        return
    
    media_m3u8 = HLSMediaPlaylist(text=resp)
    
    # get the init
    resp = scrape(url=media_m3u8.uri, headers=HEADERS, decode=False)
    if (resp != None):
        file: Path = TEMPDIR / media_m3u8.init_segment_filename
        file.write_bytes(resp)
            
    # using multiprocessing
    with concurrent.futures.ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
        list(tqdm(
            executor.map(
                scrape_segment_with_multiprocessing, # the function
                media_m3u8.segments, # the segments
                itertools.repeat(HEADERS), # constant 1: header
                itertools.repeat(TEMPDIR), # constant 2: temp folder
            ),
            total=media_m3u8.no_of_segments,
            desc="Downloading segments",
            unit="seg",
        ))
    
    # combine the segments
    combine_segments(temp_dir=TEMPDIR, expected_no_of_segments=media_m3u8.no_of_segments)


if (__name__ == "__main__"):
    main()
