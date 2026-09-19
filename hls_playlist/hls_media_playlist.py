import re

from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse


class InvalidMediaPlaylistFormatError(ValueError):
    """Raised when the input string is not a valid HLS media playlist."""
    pass

class URINotFoundError(Exception):
    """Raised when the init segment uri/url cannot be found"""
    pass


@dataclass
class HLSMediaSegment:
    url: str
    segment: int
    filename: str


@dataclass
class _ParsedMedia:
    # the important bit
    init_url: str = ""

    # the additional details
    target_duration: int = 0
    allow_cache: str = ""
    playlist_type: str = ""
    version: int = 0
    media_sequence: int = 0
    
    # the segments
    no_of_segments: int = 0
    segments: list[HLSMediaSegment] = field(default_factory=lambda: [])


@dataclass
class HLSMediaPlaylist:
    # the important bits
    uri: str
    init_segment_filename: str
    segments: list[HLSMediaSegment]
    no_of_segments: int
    
    # the additional details
    target_duration: int
    allow_cache: str
    playlist_type: str
    version: int
    media_sequence: int
    
    def __init__(self, text: str, base_url: str = ""):
        parsed_ = self._parse(text, base_url)

        # the important bits - the init segment details
        self.uri = parsed_.init_url
        self.init_segment_filename = urlparse(self.uri).path.split("/")[-1]

        # the important bits - the segments
        self.no_of_segments = parsed_.no_of_segments
        self.segments = parsed_.segments
        
        # the additional details
        self.target_duration = parsed_.target_duration
        self.allow_cache = parsed_.allow_cache
        self.playlist_type = parsed_.playlist_type
        self.version = parsed_.version
        self.media_sequence = parsed_.media_sequence
    
    
    def _parse(self, text: str, base_url: str = "") -> _ParsedMedia:
        """
        A comprehensive parsing function to check if the text string received is a valid HLS media playlist.
        """
        lines: list[str] = text.splitlines()
        non_blank: list[str] = [l for l in lines if l.strip()]
        if not non_blank or non_blank[0].strip() != "#EXTM3U":
            raise InvalidMediaPlaylistFormatError("'#EXTM3U' tag not found")
        
        # initialise the values
        current_map: str | None = None
        parsed_: _ParsedMedia = _ParsedMedia()
        
        # iterate the lines
        expect_uri: bool = False; found_endlist: bool = False
        for raw in lines:
            line: str = raw.strip()
            
            # skip blank (legal), don't break
            if not line:
                continue
            
            # get the playlist type first: VOD or Live
            if line.startswith("#EXT-X-PLAYLIST-TYPE"):
                playlist_type_search: re.Match[str] | None = re.search(r'#EXT-X-PLAYLIST-TYPE:(.*)', line)
                if (playlist_type_search != None):
                    parsed_.playlist_type = playlist_type_search.group(1)
            
            # VOD (Video on Demand): finished movie - playlist ends
            if (parsed_.playlist_type == "VOD" and found_endlist):
                raise InvalidMediaPlaylistFormatError("additional lines after encountering '#EXT-X-ENDLIST'")

            # encrpted segments: not supported
            if (line.startswith("#EXT-X-KEY")):
                encrypted_search = re.search(r'#EXT-X-KEY.*METHOD=AES-128')
                if (encrypted_search):
                    raise InvalidMediaPlaylistFormatError("encrypted streams not supported yet")
            
            # partial segments: not supported
            if (line.startswith("#EXT-X-BYTERANGE")):
                raise InvalidMediaPlaylistFormatError("byte range within segment file not supported yet")
            
            if line.startswith("#EXT-X-TARGETDURATION"):
                target_duration_search: re.Match[str] | None = re.search(r'#EXT-X-TARGETDURATION:(.*)', line)
                if (target_duration_search != None):
                    if (target_duration_search.group(1).isdigit()):
                        parsed_.target_duration = int(target_duration_search.group(1))
                    else:
                        raise InvalidMediaPlaylistFormatError("target duration not a valid integer")
            
            if line.startswith("#EXT-X-ALLOW-CACHE"):
                allow_cache_search: re.Match[str] | None = re.search(r'#EXT-X-ALLOW-CACHE:(.*)', line)
                if (allow_cache_search != None):
                    parsed_.allow_cache = allow_cache_search.group(1)
            
            if line.startswith("#EXT-X-VERSION"):
                version_search: re.Match[str] | None = re.search(r'#EXT-X-VERSION:(.*)', line)
                if (version_search != None):
                    if (version_search.group(1).isdigit()):
                        parsed_.version = int(version_search.group(1))
                    else:
                        raise InvalidMediaPlaylistFormatError("version not a valid integer")
            
            if line.startswith("#EXT-X-MEDIA-SEQUENCE"):
                media_sequence_search: re.Match[str] | None = re.search(r'#EXT-X-MEDIA-SEQUENCE:(.*)', line)
                if (media_sequence_search != None):
                    if (media_sequence_search.group(1).isdigit()):
                        parsed_.media_sequence = int(media_sequence_search.group(1))
                    else:
                        raise InvalidMediaPlaylistFormatError("media sequence not a valid integer")
            
            if line.startswith("#EXT-X-MAP"):
                if (current_map): # already found a URI
                    raise InvalidMediaPlaylistFormatError("multiple MAPs currently not supported")

                map_search: re.Match[str] | None = re.search(r'#EXT-X-MAP:URI="([^"]+)"', line)
                if (not map_search):
                    raise URINotFoundError("Fail to get the init segment URI/URL")
                
                parsed_.init_url = urljoin(base_url, map_search.group(1))
                current_map = parsed_.init_url
                
            if line.startswith("#EXTINF"):
                duration_search: re.Match[str] | None = re.search(r'#EXTINF:(.*),', line)
                if (not duration_search):
                    raise InvalidMediaPlaylistFormatError("segment timing invalid")

                try:
                    float(duration_search.group(1))
                except ValueError:
                    raise InvalidMediaPlaylistFormatError("segment timing invalid")
                
                expect_uri = True
                
            if expect_uri and self._is_uri(line):
                parsed_.no_of_segments += 1
                new_segment = HLSMediaSegment(
                    segment=parsed_.no_of_segments,
                    url=urljoin(base_url, line),
                    filename=f"seg-{parsed_.no_of_segments}.m4s"
                )
                parsed_.segments.append(new_segment)
                expect_uri = False
                
            if line.startswith("#EXT-X-ENDLIST"):
                found_endlist = True
        
        # must end with "#EXT-X-ENDLIST"
        if (parsed_.playlist_type == "VOD" and not found_endlist):
            raise InvalidMediaPlaylistFormatError("playlist type is VOD but '#EXT-X-ENDLIST' tag not found")
        
        # must not end with uri
        if (parsed_.playlist_type == "VOD" and expect_uri):
            raise InvalidMediaPlaylistFormatError("playlist type is VOD but ending with a URI")
        
        return parsed_
    
    @staticmethod
    def _is_uri(line: str) -> bool:
        """A URI is a non-empty line that isn't a tag"""
        s = line.strip()
        # `bool(s)` means non-empty
        # `not s.startswith("#")` means not a tag
        # `" " not in s` means no empty spaces 
        return bool(s) and not s.startswith("#") and " " not in s