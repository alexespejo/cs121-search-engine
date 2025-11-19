from pathlib import Path
from typing import Literal
import shutil
import os

BYTES_TO_KB = 1024
BYTES_TO_MB = 1024**2
BYTES_TO_GB = 1024**3
BYTES_TO_TB = 1024**4

def is_valid_dir(path: Path):
    return path.exists() and path.is_dir()

def is_valid_file(path: Path):
    return path.exists() and path.is_file()

def get_dir_size(path: Path, recursive: bool = False, unit: Literal["bytes", "KB", "MB", "GB", "TB"] = "KB"):
    """
    Returns the total size (in bytes) of files inside a directory.

    By default, only files directly inside the directory are counted.
    Set recursive=True to sum all files in subdirectories as well.
    """

    total_bytes = 0

    if recursive:
        # Walk the entire tree
        for root, dirs, files in os.walk(path):
            for f in files:
                fp = os.path.join(root, f)
                if os.path.isfile(fp):
                    total_bytes += os.path.getsize(fp)
    else:
        # Only the top-level directory
        for f in os.listdir(path):
            fp = os.path.join(path, f)
            if os.path.isfile(fp):
                total_bytes += os.path.getsize(fp)

    unit_factors = {
        "bytes": 1,
        "KB": BYTES_TO_KB,
        "MB": BYTES_TO_MB,
        "GB": BYTES_TO_GB,
        "TB": BYTES_TO_TB,
    }

    return total_bytes / unit_factors[unit]

def rm_dir(
    path: Path,
    recursive: bool = True,
    ignore_missing: bool = True,
    only_contents: bool = False
) -> None:
    """
    Deletes a directory or its contents.

    Parameters:
        path          : Directory to remove.
        recursive     : If True, delete the directory and all subdirectories.
                        If False, deletion will fail if the directory is not empty.
        ignore_missing: If True, do nothing when the directory doesn't exist.
        only_contents : If True, delete everything inside the directory but keep the directory itself.

    Raises:
        FileNotFoundError: If directory does not exist and ignore_missing=False.
        OSError         : For permission or filesystem errors.
    """

    if not is_valid_dir(path):
        if ignore_missing:
            return
        raise FileNotFoundError(f"Directory not found: {path}")

    if only_contents:
        # Remove everything inside the directory, but keep the directory itself
        for item in os.listdir(path):
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path):
                shutil.rmtree(full_path)
            else:
                os.remove(full_path)
        return

    if recursive:
        shutil.rmtree(path)
    else:
        # Non-recursive: remove only if empty
        os.rmdir(path)
