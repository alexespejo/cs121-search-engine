from pathlib import Path
from typing import Literal
import shutil
import os
import pickle

import utils.constants as const

from logging import getLogger

logger = getLogger(__name__)

def get_json_file_list(data_dir_str: str) -> list[Path]:
    """Return list of all JSON files in a directory."""
    data_path: Path = Path(data_dir_str)
    if (not is_valid_dir(data_path)):
        error_message: str = f"Data directory {data_path} is invalid"
        logger.error(error_message)
        raise FileNotFoundError(error_message)
    file_list = sorted([p for p in data_path.rglob("*.json") if p.is_file()])
    return file_list

def save_file_list(file_list: list[Path]):
    with open("file_list.pkl", "wb") as f:
        pickle.dump(file_list, f)

def load_file_list(file_list_str: str) -> list[Path]:
    file_list_path = Path(file_list_str)
    if (not is_valid_file(file_list_path)):
        error_message: str = f"File list path: {file_list_path} is invalid"
        logger.error(error_message)
        raise FileNotFoundError(error_message)
    
    with open(file_list_path, "rb") as f:
        file_list: list[Path] = pickle.load(f)
        return file_list

class FilePointer:
    def __init__(self, file_idx: int = 0, batch_counter: int = 0):
        self.file_idx: int = file_idx
        self.batch_counter: int = batch_counter
        self.path: Path = const.TMP_DIR / Path("cursor.pkl")

    def exists_on_disk(self) -> bool:
        return self.path.exists()
    
    def save_pointer(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load_pointer(cls) -> "FilePointer":
        """Load the pointer from disk. Returns a FilePointer instance."""
        path: Path = const.TMP_DIR / Path("cursor.pkl")
        if not path.exists():
            raise FileNotFoundError(f"No pointer file found at {path}")
        with open(path, "rb") as f:
            obj = pickle.load(f)
        if not isinstance(obj, cls):
            raise TypeError(f"Expected a FilePointer object, got {type(obj)}")
        return obj


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
        "KB": const.BYTES_TO_KB,
        "MB": const.BYTES_TO_MB,
        "GB": const.BYTES_TO_GB,
        "TB": const.BYTES_TO_TB,
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


