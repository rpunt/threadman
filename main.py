#!/usr/bin/env python3

"""
Example usage of ThreadManager to process a list of items concurrently.
This script demonstrates how to create a ThreadManager instance, configure it with options,
and run a task function on multiple threads.
"""

from threadman import ThreadManager


def my_task(item): # pylint: disable=missing-function-docstring
    print(f"Processing {item}")


items = [1, 2, 3, 4, 5]
opts = {
    "work_params": items,
    "max_threads": 3,
    "progress_bar_title": "Processing Items",
    "output_status": True,
}

tm = ThreadManager(opts)
tm.run(my_task)
