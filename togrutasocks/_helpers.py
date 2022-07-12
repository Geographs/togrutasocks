import asyncio
import typing

import aiofiles
import socks
from textual import widget


async def check_proxy(
    loop: asyncio.AbstractEventLoop,
    proxy_type: typing.Literal[1, 2, 3],
    address: tuple[str, int],
) -> bool:
    socket = socks.socksocket()
    socket.set_proxy(proxy_type)

    try:
        await loop.sock_connect(socket, address)
    except OSError:
        return False
    finally:
        socket.close()
    return True


async def load_lines(file: str) -> list[str]:
    async with aiofiles.open(file, "r", encoding="utf-8", errors="ignore") as file:
        return (await file.read()).split("\n")


def parse_into_addresses(lines: list[str]) -> list[tuple[str, int]]:
    addresses: list[tuple[str, int]] = []

    for line in lines:
        if ":" in line:
            split: list[str] = line.split(":")
            if len(split) == 2:
                if split[1].isnumeric():
                    addresses.append((split[0], int(split[1])))

    return addresses


async def make_visible_for(widget: widget.Widget, seconds: int) -> None:
    widget.visible = True
    await asyncio.sleep(seconds)
    widget.visible = False
