# pylint: disable=missing-function-docstring

import os
import sys
import time
import threading
from threadman import ThreadManager
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def test_basic_execution():
    results = []
    def task(x):
        results.append(x * 2)
    items = [1, 2, 3]
    opts = {"work_params": items, "max_threads": 2}
    manager = ThreadManager(opts)
    manager.run(task)
    # Wait for all tasks to finish
    manager.work_queue.join()
    assert sorted(results) == [2, 4, 6]

def test_thread_limit():
    active_threads = set()
    lock = threading.Lock()
    def task(x):
        with lock:
            active_threads.add(threading.current_thread().name)
        time.sleep(0.1)
    items = list(range(5))
    opts = {"work_params": items, "max_threads": 2}
    manager = ThreadManager(opts)
    manager.run(task)
    manager.work_queue.join()
    # There should not be more than 2 unique worker threads at a time
    assert all(name.startswith("Worker-") for name in active_threads)
    assert len(active_threads) <= 5  # Should not exceed number of tasks

def test_progress_bar_and_output(caplog):
    items = [1, 2]
    opts = {
        "work_params": items,
        "max_threads": 1,
        "progress_bar_title": "Test",
        "output_status": True,
    }
    manager = ThreadManager(opts)
    with caplog.at_level("INFO"):
        manager.run(lambda x: None)
    manager.work_queue.join()
    assert "Execution is complete" in caplog.text


def test_error_handling():
    items = [1, 2]
    opts = {"work_params": items, "max_threads": 1, "output_status": True}
    manager = ThreadManager(opts)
    def bad_task(x):
        raise ValueError("fail")
    manager.run(bad_task)
    manager.work_queue.join()  # Should not raise, and should complete
