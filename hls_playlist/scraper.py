import time
import urllib.request

from pathlib import Path
from hls_playlist.hls_media_playlist import HLSMediaSegment


def scrape_segment_with_multiprocessing(
    media_segment: HLSMediaSegment,
    headers: dict[str, str],
    folderpath: Path,
) -> None:    
    resp = scrape(url=media_segment.url, headers=headers, decode=False)
    if (resp != None):
        file = folderpath / media_segment.filename
        file.write_bytes(resp)


def scrape(
    url: str,
    headers: dict[str, str],
    retries: int = 3,
    timeout: int = 15,
    decode: bool = True,
    decode_encoding: str = "utf-8"
) -> str | None:
    """
    Get the response data from the URL with the headers.
    
    @param url: the full url with "https://..."
    @param headers: the headers associated with the GET request
    @param decode: whether to decode the response
    @param decode_encoding: the encoding used to decode the response
    """
    for attempt in range(retries):
        
        try:
            req = urllib.request.Request(url=url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                status = response.status
                if (status == 200):
                    data = response.read()
                    return data.decode(decode_encoding) if decode else data
        
        except (urllib.request.HTTPError, TimeoutError) as e:
            if attempt == retries-1:
                print(f"FAILED {url}: {e}")
            else:
                time.sleep(1.5 ** attempt)
    
    return None