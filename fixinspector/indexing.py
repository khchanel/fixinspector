from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from fixinspector.core.dictionary import FixDictionary
from fixinspector.core.models import MessageSummary
from fixinspector.core.parser import CHECKSUM_RE, decode_fix_message


@dataclass(frozen=True)
class IndexEntry:
    row: int
    offset: int
    length: int
    summary: MessageSummary


ProgressCallback = Callable[[int, int | None], None]
CancelCallback = Callable[[], bool]


def index_file(
    path: str | Path,
    dictionary: FixDictionary | None = None,
    chunk_size: int = 1024 * 1024,
    progress: ProgressCallback | None = None,
    should_cancel: CancelCallback | None = None,
) -> list[IndexEntry]:
    return list(iter_index_file(path, dictionary, chunk_size, progress, should_cancel))


def iter_index_file(
    path: str | Path,
    dictionary: FixDictionary | None = None,
    chunk_size: int = 1024 * 1024,
    progress: ProgressCallback | None = None,
    should_cancel: CancelCallback | None = None,
) -> Iterable[IndexEntry]:
    source = Path(path)
    dictionary = dictionary or FixDictionary.common()
    total = source.stat().st_size if source.exists() else None
    buffer = ""
    buffer_offset = 0
    row = 0

    with source.open("rb") as handle:
        while True:
            if should_cancel and should_cancel():
                return
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            buffer += chunk.decode("latin1", errors="replace")
            consumed = 0
            while True:
                start = buffer.find("8=FIX")
                if start < 0:
                    keep = min(len(buffer), 32)
                    consumed = len(buffer) - keep
                    buffer = buffer[-keep:]
                    buffer_offset += consumed
                    break
                match = CHECKSUM_RE.search(buffer, start)
                if match is None:
                    if start > 0:
                        buffer_offset += start
                        buffer = buffer[start:]
                    break
                raw = buffer[start:match.end()]
                message = decode_fix_message(raw, dictionary)
                offset = buffer_offset + start
                length = match.end() - start
                yield IndexEntry(row=row, offset=offset, length=length, summary=message.summary)
                row += 1
                consumed = match.end()
                buffer = buffer[consumed:]
                buffer_offset += consumed
            if progress:
                progress(handle.tell(), total)


def read_indexed_message(path: str | Path, entry: IndexEntry, dictionary: FixDictionary | None = None):
    source = Path(path)
    with source.open("rb") as handle:
        handle.seek(entry.offset)
        raw = handle.read(entry.length).decode("latin1", errors="replace")
    return decode_fix_message(raw, dictionary or FixDictionary.common())
