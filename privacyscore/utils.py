"""
Utility functions that are shared across different modules.
"""
import errno
import fcntl
import os
from pathlib import Path

from pwd import getpwuid
from typing import List, Tuple

from urllib.parse import urlparse
from url_normalize import url_normalize


def normalize_url(url: str) -> str:
    """Normalize an url and remove GET query."""
    url = url.strip()
    normalized = url_normalize(url)
    parsed = urlparse(normalized)
    if parsed.port:
        normalized = normalized.replace(
            ':{}'.format(parsed.port), '', 1)
    if parsed.username is not None and parsed.password is not None:
        normalized = normalized.replace(
            '{}:{}@'.format(parsed.username, parsed.password), '', 1)
    elif parsed.username is not None:
        normalized = normalized.replace(
            '{}@'.format(parsed.username), '', 1)
    return normalized.split('?')[0]


def get_raw_data_by_identifier(raw_data: list, identifier: str):
    """Get the first raw data element with the specified identifier."""
    return next((
        r[1] for r in raw_data if r[0]['identifier'] == identifier), None)


def get_list_item_by_dict_entry(search: list, key: str, value: str):
    """Get the first raw data element with the specified value for key."""
    return next((
        s for s in search if s[key] == value), None)


def get_processes_of_user(user: str) -> List[Tuple[int, str]]:
    """Get a tuple (pid, cmdline) for all processes of user."""
    return [
        (int(pid),
         open('/proc/{}/cmdline'.format(pid), 'r').read())
        for pid in os.listdir('/proc')
        if (pid.isdigit() and
            getpwuid(os.stat('/proc/{}'.format(pid)).st_uid).pw_name == user)]


class get_worker_id:
    def __init__(self, ident='worker-ids'):
        self.ident = ident
        self._worker_lock_dir = Path('/dev/shm/') / ident
        self._lock_file = None

    def __enter__(self):
        self._worker_lock_dir.mkdir(exist_ok=True)
        worker_id = 0
        while True:
            self._lock_file = open(self._worker_lock_dir / str(worker_id), 'w')
            try:
                fcntl.lockf(self._lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return worker_id
            except OSError as e:
                if e.errno not in (errno.EAGAIN, errno.EACCES):
                    raise
            worker_id += 1

    def __exit__(self, exc_type, exc_value, traceback):
        if self._lock_file:
            fcntl.lockf(self._lock_file.fileno(), fcntl.LOCK_UN)
            self._lock_file.close()
