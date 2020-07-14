# -*- coding: utf-8 -*-
# custom_types.py
# Copyright (C) 2020 KunoiSayami
#
# This module is part of python-process-monitor-win and is released under
# the AGPL v3 License: https://www.gnu.org/licenses/agpl-3.0.txt
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
import asyncio
from dataclasses import dataclass
from typing import Dict, List, Tuple, TypeVar

import aiohttp
import aiofiles

mixTypes = TypeVar('mixTypes', str, int, bool, List[Tuple[str, str]])




@dataclass(init=False)
class RemoteVersion:
    '''
    Description of RemoteVersion object:

    Network object should use valid json format.
    And should use following format:
    {
        'version': unsigned int,
        'urls': [[str, str], [str, str], ...]
        'need_restart': bool
    }
    '''
    version: int
    update_urls: List[Tuple[str, str]]
    need_restart: bool

    def __init__(self, rep: Dict[str, mixTypes]) -> None:
        self.version = int(rep['version'])
        self.update_urls = rep['urls']
        self.need_restart = bool(rep['need_restart'])

    async def download(self, session: aiohttp.ClientSession) -> None:
        for url, file_name in self.update_urls:
            async with session.post(url) as req, aiofiles.open(file_name, 'wb') as fout:
                for chunk in req.iter(chunk=1024):
                    if not chunk:
                        break
                    await fout.write(chunk)

@dataclass
class TaskControl:
    task: asyncio.Task

    def __call__(self, *args) -> None:
        self.task.cancel()