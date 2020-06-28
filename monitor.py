# -*- coding: utf-8 -*-
# main.py
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
import hashlib
import logging
import os
import signal
import sys
from dataclasses import dataclass
from signal import SIGINT

import aiosqlite
import psutil

logger = logging.getLogger('statistics')
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler('log.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(funcName)s - %(lineno)d - %(message)s'))
logger.addHandler(file_handler)

@dataclass
class TaskControl:
	task: asyncio.Task

	def __call__(self, *args) -> None:
		self.task.cancel()

async def main() -> None:
	with open('.pid', 'w') as fout:
		fout.write(str(os.getpid()))
	task = asyncio.create_task(boostrap_main())
	signal.signal(SIGINT, TaskControl(task))
	await asyncio.wait([task])

async def init() -> None:
	if not os.path.exists('local.db'):
		async with aiosqlite.connect('local.db') as db:
			await db.execute('''CREATE TABLE "current_process" (
											"hash"	TEXT,
											PRIMARY KEY("hash")
							) WITHOUT ROWID;''')
			await db.execute('''CREATE TABLE "process_record" (
								"process"	TEXT,
								"timestamp"	INTEGER,
								"path"	TEXT
							);''')
			await db.commit()
		logger.info('Initialize successfully')

async def boostrap_main() -> None:
	await init()
	await monitor(True)
	while True:
		try:
			await monitor()
			logger.info('Success')
		except:
			logger.exception('Got unexcept exception in main thread, ignored.')
		finally:
			await asyncio.sleep(60)

async def monitor(init: bool=False) -> None:
	conn = await aiosqlite.connect('local.db')
	if init:
		await conn.execute("DELETE FROM `current_process`")
		await conn.commit()
	for process in psutil.process_iter():
		try:
			#print(process.name(), process.pid, process.exe(), process.create_time())
			h = hashlib.sha256(f'{process.pid}{int(process.create_time())}'.encode()).hexdigest()
			cur = await conn.execute(f"SELECT * FROM `current_process` WHERE `hash` = ?", (h,))
			if await cur.fetchone() is None:
				await conn.execute("INSERT INTO `current_process` (`hash`) VALUES (?)", (h,))
				await conn.execute("INSERT INTO `process_record` (`process`, `timestamp`, `path`) VALUES (?, ?, ?)", (process.name(), int(process.create_time()), process.exe()))
				logger.debug('Insert new process %s(%d)[%s]', process.name(), process.pid, process.exe())
				#await conn.commit()
			await cur.close()
		except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
			pass
	await conn.commit()
	await conn.close()

if __name__ == "__main__":
	if len(sys.argv) > 1 and sys.argv[1] == 'stop':
		with open('.pid') as fin:
			os.kill(int(fin.read()), 2)
	else:
		logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(funcName)s - %(lineno)d - %(message)s')
		loop = asyncio.get_event_loop()
		#loop.set_debug(True)
		loop.run_until_complete(main())
		loop.close()
