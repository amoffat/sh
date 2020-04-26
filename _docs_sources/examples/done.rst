Here's an example of using :ref:`done` to create a multiprocess pool, where
``sh.your_parallel_command`` is executed concurrently at no more than 10 at a
time:

.. code-block:: python

    import sh
    from threading import Semaphore

    pool = Semaphore(10)

    def done(cmd, success, exit_code):
        pool.release()

    def do_thing(arg):
        pool.acquire()
        return sh.your_parallel_command(arg, _bg=True, _done=done)

    procs = []
    for arg in range(100):
        procs.append(do_thing(arg))

    # essentially a join
    [p.wait() for p in procs]
