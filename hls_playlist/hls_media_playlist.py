import re

from dataclasses import dataclass


class InvalidMediaPlaylistFormatError(ValueError):
    """Raised when the input string is not a valid HLS media playlist."""
    pass


@dataclass
class HLSMediaSegment:
    url: str
    segment: int
    filename: str


@dataclass
class HLSMediaPlaylist:
    
    target_duration: int
    allow_cache: str
    playlist_type: str
    version: int
    media_sequence: int
    uri: str
    segments: list[HLSMediaSegment]
    no_of_segments: int
    
    def __init__(self, text: str):
        
        if (not self._is_hls_media_playlist_format(text)):
            raise InvalidMediaPlaylistFormatError("Input is not a valid HLS media playlist (.m3u8)")
        
        # get the attributes
        attributes: dict[str, str] = self._get_media_playlist_details(text=text)
        
        # the init*.mp4 url
        map_re = re.compile(r'.*"(https://.*.mp4)"')
        map = map_re.findall(attributes.get("map"))
        self.uri = None if len(map) < 0 else map[0]
                
        # the attributes of the media playlist
        self.target_duration = attributes.get("targetduration")
        self.allow_cache = attributes.get("allow-cache")
        self.playlist_type = attributes.get("playlist-type")
        self.version = attributes.get("version")
        self.media_sequence = attributes.get("media-sequence")
        
        # the complete segments
        self.no_of_segments = attributes.get("no_of_segments")
        self.segments = []
        for i in range(self.no_of_segments):
            self.segments.append(
                HLSMediaSegment(
                    segment=i+1,
                    url=attributes.get("segments").get(i + 1),
                    filename=f"seg-{i+1}.m4s"
                )
            )
    
    
    def _get_media_playlist_details(self, text: str) -> dict[str, str] | None:
        
        lines = text.splitlines()
        non_blank = [l for l in lines if l.strip()]
        if not non_blank or non_blank[0].strip() != "#EXTM3U":
            return [] # must be FIRST line
        
        attributes: dict[str, str | dict[int, str]] = {}
        segments: dict[int, str] = {}
        no_of_segments, expect_uri = 0, False
        for raw in lines:
            line = raw.strip()
            
            # skip blank (legal), don't break
            if not line:
                continue
            
            if line.startswith("#EXT-X-") and not line.startswith("#EXT-X-ENDLIST"):
                attr_re = re.compile(r'#EXT-X-(.*?):(.*)')
                found = attr_re.findall(line)
                if (len(found) < 0):
                    continue
                
                key, value = attr_re.findall(line)[0]
                attributes[key.lower()] = value
                
            if line.startswith("#EXTINF"):
                expect_uri = True
                
            if expect_uri and self._is_uri(line):
                no_of_segments += 1
                segments[no_of_segments] = line
                expect_uri = False
        
        # set the segments to the attributes
        attributes["no_of_segments"] = no_of_segments
        attributes["segments"] = segments
        
        return attributes
    
    def _is_hls_media_playlist_format(self, text: str) -> bool:
        
        lines = text.splitlines()
        non_blank = [l for l in lines if l.strip()]
        if not non_blank or non_blank[0].strip() != "#EXTM3U":
            return [] # must be FIRST line
        
        found_endlist, expect_uri = False, False
        for raw in lines:
            line = raw.strip()
            
            # skip blank (legal), don't break
            if not line:
                continue
            
            if line.startswith("#EXT-X-") and not line.startswith("#EXT-X-ENDLIST"):
                attr_re = re.compile(r'#EXT-X-(.*?):(.*)')
                found = attr_re.findall(line)
                if (len(found) < 0):
                    return False
                if expect_uri:
                    return False
                
            elif line.startswith("#EXTINF"):
                expect_uri = True
            
            elif line.startswith("#EXT-X-ENDLIST"):
                found_endlist = True
            
            else:
                if expect_uri and not self._is_uri(line):
                    return False
                expect_uri = False
                
        return found_endlist and not expect_uri
    
    def _is_uri(self, line: str) -> bool:
        """A URI is a non-empty line that isn't a tag"""
        s = line.strip()
        # `bool(s)` means non-empty
        # `not s.startswith("#")` means not a tag
        # `" " not in s` means no empty spaces 
        return bool(s) and not s.startswith("#") and " " not in s