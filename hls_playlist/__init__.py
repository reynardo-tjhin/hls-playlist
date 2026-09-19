"""hls_playlist: parse HLS master playlists (``.m3u8``)."""

from hls_playlist.hls_master_playlist import (
    HLSMasterPlaylist,
    InvalidPlaylistFormatError,
)
from hls_playlist.hls_media_playlist import (
    HLSMediaPlaylist,
    InvalidMediaPlaylistFormatError,
)
from hls_playlist.read_curl import read_curl_command
from hls_playlist.scraper import scrape, scrape_segment_with_multiprocessing
from hls_playlist.combine_segments import combine_segments


__all__ = [
    "HLSMasterPlaylist",
    "InvalidPlaylistFormatError",
    "HLSMediaPlaylist",
    "InvalidMediaPlaylistFormatError",
    "read_curl_command",
    "scrape",
    "scrape_segment_with_multiprocessing",
    "combine_segments",
]