"""Parse HLS master playlists (``.m3u8``).

Turns the raw text of an HLS master playlist into structured objects:
:class:`HLSMasterPlaylist` holds a list of :class:`HLSStreamMediaVariant`,
one per ``#EXT-X-STREAM-INF`` entry.

Example:
    >>> from hls_playlist import HLSMasterPlaylist
    >>> playlist = HLSMasterPlaylist(text)
    >>> for v in playlist.media_variants:
    ...     print(v.bandwidth, v.resolution, v.uri)
"""
import re

from dataclasses import dataclass


class InvalidPlaylistFormatError(ValueError):
    """Raised when the input string is not a valid HLS master playlist."""
    pass


@dataclass
class HLSStreamMediaVariant():
    """A single media variant (stream) offered by a master playlist.

    Attributes:
        program_id: The ``PROGRAM-ID`` value, or ``None`` if absent.
        bandwidth: Maximum bandwidth in bits per second.
        resolution: Video size as ``"WIDTHxHEIGHT"`` (e.g. ``"1920x1080"``).
        frame_rate: The ``FRAME-RATE`` value, or ``None`` if absent.
        codecs: The ``CODECS`` value, or ``None`` if absent.
        uri: URI of this variant's media playlist.
    """
    program_id: str | None
    bandwidth: int
    resolution: str
    frame_rate: str | None
    codecs: str | None
    uri: str


@dataclass
class HLSMasterPlaylist:
    """A parsed HLS master playlist.

    Built from the raw text of a ``.m3u8`` master playlist. The text is
    validated before any parsing; if it is not a well-formed master playlist,
    construction raises and no object is created.

    Attributes:
        media_variants: The media variants parsed from the playlist, in the
            order they appear.

    Example:
        >>> playlist = HLSMasterPlaylist(text)
        >>> playlist.media_variants[0].bandwidth
        6126617
    """
    media_variants: list[HLSStreamMediaVariant]
    
    def __init__(self, text: str):
        """Validate and parse a master playlist.

        Args:
            text: The full raw text of a ``.m3u8`` master playlist.

        Raises:
            InvalidPlaylistFormatError: If ``text`` is not a valid HLS master
                playlist.
        """
        if (not self._is_hls_master_playlist_format(text)):
            raise InvalidPlaylistFormatError("Input is not a valid HLS master playlist (.m3u8)")
        
        self.media_variants = []
        var = self._get_variants_and_its_attributes(text)
        for v in var:
            self.media_variants.append(
                HLSStreamMediaVariant(
                    program_id=v.get("program-id"),
                    bandwidth=int(v.get("bandwidth")),
                    resolution=v.get("resolution"),
                    frame_rate=v.get("frame-rate"),
                    codecs=v.get("codecs"),
                    uri=v.get("uri"),
                )
            )
    
    
    def _get_variants_and_its_attributes(self, text: str) -> list[dict[str, str]]:
        """Extract each variant's attributes and its URI.

        Walks the playlist lines, collecting one attribute dict per
        ``#EXT-X-STREAM-INF`` tag and attaching the following URI line to it.

        Args:
            text: The raw master playlist text (assumed already validated).

        Returns:
            A list with one dict per variant. Each dict holds the lower-cased
            attribute key/value pairs plus a ``"uri"`` key.
        """
        
        variants = []
        lines = text.splitlines()
        # State machine: after a #EXT-X-STREAM-INF we expect its URI next.
        expect_uri = False
        for raw in lines:
            
            line = raw.strip()
            if line.startswith("#EXT-X-STREAM-INF"):
                attrs = self._parse_stream_inf(line)
                variants.append(attrs)
                expect_uri = True

            elif self._is_uri(line):
                if (expect_uri):
                    variants[ len(variants) - 1 ]["uri"] = line
                    expect_uri = False
        
        return variants
    
    
    def _is_hls_master_playlist_format(self, text: str) -> bool:
        """Return whether ``text`` is a well-formed HLS master playlist.

        A valid master playlist:
            * starts with ``#EXTM3U`` on its first non-blank line,
            * has at least one ``#EXT-X-STREAM-INF`` variant,
            * has a URI line after every ``#EXT-X-STREAM-INF``, and
            * has a numeric ``bandwidth`` on every variant.

        Args:
            text: The raw playlist text to validate.

        Returns:
            True if the text is a valid master playlist, else False.
        """
        
        # get the lines
        lines = text.splitlines()
        non_blank = [l for l in lines if l.strip()]
        if not non_blank or non_blank[0].strip() != "#EXTM3U":
            return False # must be FIRST line

        # expect_uri is a boolean flag to indicate it expects URI after every "#EXT-X-STREAM-INF"
        variants, expect_uri = 0, False
        for raw in lines:
            line = raw.strip()

            # skip blank (legal), don't break
            if not line:
                continue
                
            # tag with no URI before it
            if line.startswith("#EXT-X-STREAM-INF"):
                if expect_uri:
                    return False
                if self._parse_stream_inf(line) is None: # invalid tag
                    return False
                variants += 1
                expect_uri = True
            
            # #EXT-X-MEDIA, #EXTM3U, etc.
            elif line.startswith("#"):
                continue
            
            else:
                if not expect_uri or not self._is_uri(line):
                    return False # URI out of place / malformed
                expect_uri = False

        return variants > 0 and not expect_uri # last tag must have a URI
    
    
    def _parse_stream_inf(self, line: str) -> dict[str, str] | None:
        """Parse a single ``#EXT-X-STREAM-INF`` line into its attributes.

        Args:
            line: A stripped playlist line.

        Returns:
            A dict of lower-cased attribute names to their values if ``line``
            is a valid ``#EXT-X-STREAM-INF`` with a numeric ``bandwidth``;
            otherwise None.
        """
        
        # Matches one KEY=VALUE pair: group 1 is the key, group 2 the value
        # (either "quoted" or a bare token).
        pair_re = re.compile(r'([A-Z0-9-]+)=("[^"]*"|[^,\s"]+)')
        
        # Matches a whole comma-separated attribute list; used to reject a
        # malformed list before extracting individual pairs.
        attr_list_re = re.compile(
            r'[A-Z0-9-]+=(?:"[^"]*"|[^,\s"]+)'
            r'(?:,[A-Z0-9-]+=(?:"[^"]*"|[^,\s"]+))*'
        )

        if not line.startswith("#EXT-X-STREAM-INF:"):
            return None
        
        # whole list must be clean
        attrs_str = line.split(":", 1)[1]
        if not attr_list_re.fullmatch(attrs_str):
            return None
        
        # 'bandwidth' is required
        attrs = {k.lower(): v.strip('"') for k, v in pair_re.findall(attrs_str)}
        if "bandwidth" not in attrs or not attrs["bandwidth"].isdigit():
            return None
        
        return attrs


    def _is_uri(self, line: str) -> bool:
        """Return whether a line looks like a URI.

        A URI here is a non-empty line that is not a tag (does not start with
        ``#``) and contains no whitespace.

        Args:
            line: A stripped playlist line.

        Returns:
            True if the line looks like a URI, else False.
        """
        s = line.strip()
        # bool(s): non-empty
        # not s.startswith("#"): not a tag
        # " " not in s: no whitespace
        return bool(s) and not s.startswith("#") and " " not in s