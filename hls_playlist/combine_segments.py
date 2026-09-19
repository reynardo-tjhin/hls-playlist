import re
import shutil
import subprocess

from pathlib import Path


# sort the key by segment number
def _seg_key(p: Path) -> int:
    """helper function to sort the file names by the numbers in the segment files"""
    m = re.search(r'seg-(\d+)', p.name)
    return int(m.group(1)) if m else -1 # init.mp4 -> -1, so first


def combine_segments(temp_dir: Path, output_name: str = "combined.mp4") -> None:
    """
    `temp_dir` contains all the init*.mp4 and the *.m4s segments.
    `output_name` is the .mp4 video output after combining the init*.mp4 and the *.m4s segments and running the ffmpeg command.
    
    `temp_output.mp4` will be created after combining the the segments byte-by-byte.
    `temp_output.mp4` is the intermediate output which will be removed after getting the final .mp4 video.
    
    Then runs the `ffmpeg` command.
    >> `ffmpeg -i output.mp4 -c copy combined.mp4`.
    """
    # check if temp dir exists
    if (not temp_dir.exists()):
        raise FileNotFoundError("'.temp' Folder does not exist")

    # remove the existing 'temp_output.mp4'
    temp_output_path: Path = Path(__file__).parent.parent / "temp_output.mp4"
    if (temp_output_path.exists()):
        temp_output_path.unlink()

    # write each file to the 'output.mp4' file
    with temp_output_path.open("wb") as writer:
        for file in sorted(temp_dir.glob("*.*"), key=_seg_key):
            if ("output.mp4" in file.name):
                continue
            with file.open("rb") as f:
                shutil.copyfileobj(f, writer, length=1024*1024)
                
    # run the ffmpeg command here
    try:
        subprocess.run(
            args=["ffmpeg", "-y", "-i", "temp_output.mp4", "-c", "copy", output_name],
            capture_output=False,
            text=False, # receive as a string if capture_output is set to True
            check=True, # raises an exception if the exe returns a non-zero exit code
        )
    except subprocess.CalledProcessError as e:
        print(f"ffmpeg failed with code {e.returncode}: {e}")
        return
    except FileNotFoundError:
        print("ffmpeg not found on PATH")
        return
    
    # clean up
    for file in temp_dir.glob("*.*"):
        file.unlink()
    temp_output_path.unlink()
