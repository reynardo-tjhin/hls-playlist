# hls-playlist

parses HLS master + media playlists

# TODO

1. create a class to get the master playlist (use existing one without the other media playlist)
2. if the usual "master.m3u8" does not follow the master playlist format, keep retrying with known URIs like "playlist.m3u8", etc.
3. get a list of what resolutions/bandwidths are available
4. create a simple cli to ask for which resolution/bandwidth 
5. then automatically download the media