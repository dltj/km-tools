from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Literal, TextIO

import click

from kmtools.util.config import Config, get_config

TextWriteMode = Literal["a", "w", "x"]


@contextmanager
def output_fd(
    file: str | Path,
    config: Config | None = None,
    *,
    mode: TextWriteMode = "a",
    encoding: str = "utf-8",
) -> Iterator[TextIO]:
    config = config or get_config()
    path = Path(file).expanduser()

    if config.dry_run:
        click.secho(f">>> Would write to {path} >>>", fg="green", err=True)
        yield sys.stdout
    else:
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open(mode, encoding=encoding) as fd:
            yield fd
