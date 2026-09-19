import re

def read_curl_command(text: str) -> tuple[dict[str, str], str] | None:
    """
    get the headers and the base url; using copy as cURL from browser
    
    #TODO: what if there's ?token=..., ?expires=...&signature, ?policy=...
    """
    
    # e.g.
    """
    curl --url ^"https://moon.peakstorm.top/vd/alN4NTdsbVdjUUM5ZFRMYnR4S2tRUTpIcU1vaW1sUVJKZ2pqVkQ2OVp1SWVR/master.m3u8^" ^
        -H ^"accept: */*^" ^
        -H ^"accept-language: en-US,en;q=0.8^" ^
        -H ^"cache-control: no-cache^" ^
        -H ^"origin: https://www.vidy.st^" ^
        -H ^"pragma: no-cache^" ^
        -H ^"priority: u=1, i^" ^
        -H ^"referer: https://www.vidy.st/^" ^
        -H ^"sec-ch-ua: ^\^"Brave^\^";v=^\^"153^\^", ^\^"Not_A Brand^\^";v=^\^"8^\^", ^\^"Chromium^\^";v=^\^"153^\^"^" ^
        -H ^"sec-ch-ua-mobile: ?0^" ^
        -H ^"sec-ch-ua-platform: ^\^"Windows^\^"^" ^
        -H ^"sec-fetch-dest: empty^" ^
        -H ^"sec-fetch-mode: cors^" ^
        -H ^"sec-fetch-site: cross-site^" ^
        -H ^"sec-gpc: 1^" ^
        -H ^"user-agent: Mozilla/5.0 ^(Windows NT 10.0; Win64; x64^) AppleWebKit/537.36 ^(KHTML, like Gecko^) Chrome/153.0.0.0 Safari/537.36^"
    """
    
    # first non-blank line must contain the command "curl"
    lines = text.splitlines()
    non_blank = [l for l in lines if l.strip()]
    if not non_blank or "curl" not in non_blank[0].strip():
        return None # must be FIRST line

    # get the url and the headers
    url = ""
    headers: dict[str, str] = {}
    for line in lines:
        
        # get the base URL
        if "curl" in line and "--url" in line:
            url_re = re.compile(pattern=r'curl --url \^"(.*)/.*.m3u8\^".*')
            found = url_re.findall(line)
            if (len(found) < 0):
                return None
            url = found[0]
            
        # get the headers
        elif "-H" in line:
            header_re = re.compile(pattern=r'-H \^"(.*): (.*)\^"')
            found = header_re.findall(line)
            if (len(found) > 0):
                key, value= found[0]
                value = value.replace("^(", "(")
                value = value.replace("^)", ")")
                value = value.replace("^\\", "\\")
                value = value.replace("^\"", "\"")
                value = value.replace("\\\"", "\"")
                headers[key] = value
    
    return headers, url