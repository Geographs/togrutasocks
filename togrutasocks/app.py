import asyncio
import os
import pathlib
import typing

import aiofiles
import socks
import textual_inputs
from rich import align
from rich import panel
from textual import app
from textual import events
from textual import geometry
from textual import views
from textual import widgets

from . import _helpers


class App(app.App):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()

        self._grid_view: views.GridView = views.GridView()

        self._grid_view.grid.add_column("1")
        self._grid_view.grid.add_column("2")
        self._grid_view.grid.add_column("3")
        self._grid_view.grid.add_row("1")
        self._grid_view.grid.add_row("2")
        self._grid_view.grid.add_row("3")

        # The areas are as follows:
        # 1 | 2 | 3
        # ---------
        # 4 | 5 | 6
        # ---------
        # 7 | 8 | 9
        self._grid_view.grid.add_areas(
            area_one="1,1",
            area_two="2,1",
            area_three="3,1",
            area_four="1,2",
            area_five="2,2",
            area_six="3,2",
            area_seventh="1,3",
            area_eight="2,3",
            area_nine="3,3",
        )

        self._title_label: widgets.Static = widgets.Static(
            align.Align(
                panel.Panel("TogrutaSocks by SnippyTogruta#1819"),
                "center",
                vertical="middle",
            )
        )
        self._alert_label: widgets.Static = widgets.Static("")

        self._input_dock_view: views.DockView = views.DockView()
        self._proxy_type_input: textual_inputs.TextInput = textual_inputs.TextInput(
            title="Proxy Type", placeholder="Enter Proxy Type (HTTP, SOCKS4, SOCKS5)"
        )
        self._proxy_file_input: textual_inputs.TextInput = textual_inputs.TextInput(
            title="Proxy Input File", placeholder="Enter Proxy Input File"
        )
        self._proxy_file_output: textual_inputs.TextInput = textual_inputs.TextInput(
            title="Proxy Output File", placeholder="Enter Proxy Output File"
        )

        self._start_stop_button_label: widgets.Static = widgets.Static("Start")
        self._start_stop_button: widgets.Button = widgets.Button(
            self._start_stop_button_label
        )
        self._start_stop_button_disabled: bool = False

        self._checked: int = 0
        self._good: int = 0
        self._bad: int = 0

        self._save_queue: asyncio.Queue[tuple[str, int]] = asyncio.Queue()

        self._stats_dock_view: views.DockView = views.DockView()
        self._checked_label: widgets.Static = widgets.Static("Checked: 0")
        self._good_label: widgets.Static = widgets.Static("Good: 0")
        self._bad_label: widgets.Static = widgets.Static("Bad: 0")

    async def _show_alert(self, text: str) -> None:
        await self._alert_label.update(
            align.Align(
                panel.Panel(f"Alert:\n{text}"),
                "center",
                vertical="middle",
            )
        )

        self._loop.create_task(_helpers.make_visible_for(self._alert_label, 5))

    async def _build_grid_view(self) -> None:
        await self._input_dock_view.dock(
            self._proxy_type_input, self._proxy_file_input, self._proxy_file_output
        )
        await self._stats_dock_view.dock(
            self._checked_label, self._good_label, self._bad_label
        )

        self._stats_dock_view.visible = False

        input_and_stats_dock_view: views.DockView = views.DockView()
        await input_and_stats_dock_view.dock(self._input_dock_view)
        await input_and_stats_dock_view.dock(self._stats_dock_view)

        self._grid_view.grid.place(
            area_two=self._title_label,
            area_four=self._alert_label,
            area_five=input_and_stats_dock_view,
            area_eight=self._start_stop_button,
        )

    async def on_mount(self) -> None:
        await self._build_grid_view()
        await self.view.dock(self._grid_view)

        size: os.terminal_size = os.get_terminal_size()
        await self.on_resize(
            events.Resize(
                events.MessageTarget,
                geometry.Size(width=size.columns, height=size.lines),
            )
        )

    async def handle_button_pressed(self, button: widgets.ButtonPressed) -> None:
        if button.sender == self._start_stop_button:
            if not self._start_stop_button_disabled:
                await self._handle_start_stop_button_pressed()

    async def _save_proxies(self, proxy_file_output: str) -> None:
        async with aiofiles.open(
            proxy_file_output, "a", encoding="utf-8", errors="ignore"
        ) as file:
            while True:
                proxy: tuple[str, int] = await self._save_queue.get()
                await file.write(f"{proxy[0]}:{proxy[1]}\n")

    async def _handle_start_stop_button_pressed(self) -> None:
        proxy_type: str = self._proxy_type_input.value
        proxy_file_input: str = self._proxy_file_input.value
        proxy_file_output: str = self._proxy_file_output.value

        proxy_types: dict[str, typing.Literal[1, 2, 3]] = {
            "http": socks.HTTP,
            "socks4": socks.SOCKS4,
            "socks5": socks.SOCKS5,
        }

        if (
            proxy_type in proxy_types.keys()
            and pathlib.Path(proxy_file_input).is_file()
        ):
            self._loop.create_task(self._save_proxies(proxy_file_output))
            self._update_checking_interface()
            await self._start_checking(proxy_types[proxy_type], proxy_file_input)

    async def _check_proxy(
        self, proxy_type: typing.Literal[1, 2, 3], address: tuple[str, int]
    ) -> None:
        if await _helpers.check_proxy(self._loop, proxy_type, address):
            self._good += 1
            self._save_queue.put_nowait(address)
        else:
            self._bad += 1
        self._checked += 1

    async def _start_checking(
        self, proxy_type: typing.Literal[1, 2, 3], proxy_file_input: str
    ) -> None:
        lines: list[str] = await _helpers.load_lines(proxy_file_input)
        addresses: list[tuple[str, int]] = _helpers.parse_into_addresses(lines)

        for address in addresses:
            self._loop.create_task(self._check_proxy(proxy_type, address))

    async def _update_stats(self) -> None:
        while True:
            await asyncio.sleep(1)
            await self._good_label.update(f"Good: {self._good}")
            await self._bad_label.update(f"Bad: {self._bad}")
            await self._checked_label.update(f"Checked: {self._checked}")

    def _update_checking_interface(self) -> None:
        self._loop.create_task(self._update_stats())
        self._start_stop_button_disabled = True
        self._input_dock_view.visible = False
        self._start_stop_button.visible = False
        self._stats_dock_view.visible = True
