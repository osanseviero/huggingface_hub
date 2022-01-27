import os
from pathlib import Path
from typing import Optional, Union
from urllib.error import HTTPError

import requests

from .utils import logging


logger = logging.get_logger(__name__)


def get_file_size(filename: Union[Path, str]) -> int:
    """
    Return the size of `filename` in bytes
    """
    return os.stat(filename).st_size


def shard_file(
    filename: Union[Path, str],
    shard_size: int = 1024 * 1024 * 20,
    headers: dict = {},
    identical_ok: bool = True,
    repo_id: str = None,
):
    """
    Splits `filename` into shards of size `shard_size`.
    These split files are then saved to `save_location`.

    If `save_location` is `None`, the save location will be
    the `filename` with `_shards` afterwards.

    Shards are saved with filenames starting from `0` to the total
    number of shards generated.
    """
    urls = []
    size = get_file_size(filename)
    num_shards = int(size / shard_size) + 1
    with open(filename, "rb") as infile:
        for shard_idx in range(num_shards):
            file_bytes = infile.read(shard_size)
            r = requests.post(
                f"{filename}.{str(shard_idx).zfill(5)}-of-{str(num_shards).zfill(5)}",
                headers=headers,
                data=file_bytes,
            )
            # Eventually make this more explicit
            try:
                r.raise_for_status()
            except HTTPError as err:
                raise err
            d = r.json()
            if "error" in d:
                logger.error(d["error"])
            urls.append(d.get("url", None))
    return urls


def deshard_file(filename: Union[Path, str]):
    """
    Converts a group of shards generated by `shard_file` into a single file again.
    The filename should be without the .000-of-.010 extension, such as:
      filename: filename.ext
      shards saved: filename.ext.00000-of-00001, filename.ext.00001-of-00001
    """
    filename = Path(filename)
    parent = filename.parent
    shards = []
    for file in parent.iterdir():
        # Check we are both a sharded file, and a sharded file of the intended `filename`
        if "-of" in file.suffix and file.with_suffix("").name == Path(filename).name:
            shards.append(file)

    filenames = [o for o in parent.iterdir() if "-of-" in o.suffix]
    filenames.sort()
    if filename.exists() and len(filenames) > 0:
        print(
            f"Warning: {filename} exists. Assuming it is put together and ignoring shards"
        )
        return str(filename)
    else:
        with filename.open("wb") as outfile:
            for shard in filenames:
                with shard.open("rb") as infile:
                    for line in infile:
                        outfile.write(line)
        return str(filename)