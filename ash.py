"""
http://amoffat.github.io/sh/
"""
#===============================================================================
# Copyright (C) 2018 The Qt Company Ltd.
# Contact: http://www.qt-project.org/legal
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#===============================================================================

import sh  # type: ignore
import asyncio


class _ash:
    def __init__(self, command) -> None:
        self.command = command

    def __getattr__(self, key: str):
        return _ash(getattr(self.command, key))

    def bake(self, *args, **keys):
        self.command = self.command.bake(*args, **keys)
        return self

    async def __call__(self, *args, **kwargs):
        loop = asyncio.get_event_loop()
        lock = asyncio.Lock(loop=loop)
        # Dummy acquire as fresh locks are unlocked
        await lock.acquire()
        proc = self.command(*args, **kwargs, _bg=True, _bg_exc=False, _new_session=False, _done=lambda *args: loop.call_soon_threadsafe(lock.release))
        try:
            # Blocks until _done callback is executed, which opens the lock
            await lock.acquire()
        except:
            # The operation was probably cancelled, the subprocess is not needed anymore
            try:
                proc.terminate()
            except ProcessLookupError as e:
                if e.errno != 3:  # [Errno 3] No such process
                    raise
                # We cancelled a process that managed to terminate in the same time
            raise
        return proc.wait()


ash = _ash(sh)
