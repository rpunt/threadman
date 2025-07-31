# pylint: disable=line-too-long, too-many-instance-attributes, too-few-public-methods
"""
This module provides a ThreadManager class for managing the execution of tasks using multiple threads.

The ThreadManager class allows for the concurrent execution of tasks using a specified number of threads.
It provides options to configure the number of threads, output status, and progress bar updates.

Classes:
    ThreadManager: Manages the execution of tasks using multiple threads.
"""

import logging
import queue
import threading
import time
from typing import Any, Callable, Dict, Optional, TypeVar

from tqdm import tqdm

T = TypeVar('T')  # Type variable for the work items


class ThreadManager:
    """
    Manages the execution of tasks using multiple threads.

    The ThreadManager class allows for the concurrent execution of tasks using a specified number of threads.
    It provides options to configure the number of threads, output status, and progress bar updates.

    Attributes:
        DEFAULT_MAX_THREADS (int): The default maximum number of threads.
        work_queue (queue.Queue): The queue of tasks to be executed.
        thread_mutex (threading.Lock): The mutex lock for synchronizing thread access.
        total_executions (int): The total number of tasks executed.
        current_executors (int): The current number of active executors.
        max_executions (int): The total number of tasks to be executed.
        max_threads (int): The maximum number of threads to be used.
        output (bool): Whether to output the status of the executions.
        progress_bar_title (str): The title of the progress bar.
        progress_bar (tqdm): The progress bar object.
        update_seconds (int): The interval in seconds to update the progress bar.
    """

    DEFAULT_MAX_THREADS: int = 10

    def __init__(self, opts: Optional[Dict[str, Any]] = None) -> None:
        """
        Initializes the ThreadManager with the given options.

        Args:
            opts (dict, optional): A dictionary of options to configure the ThreadManager.
                - work_params (list): A list of tasks to be executed.
                - max_threads (int): The maximum number of threads to be used.
                - output_status (bool): Whether to output the status of the executions.
                - progress_bar_title (str): The title of the progress bar.
                - update_seconds (int): The interval in seconds to update the progress bar.
                - queue_timeout (float): Timeout in seconds for queue operations. Default is None (no timeout).
                - logger (logging.Logger, optional): Custom logger instance. If not provided, a default logger will be created.
                - log_level (int, optional): Log level for the default logger if one is created. Default is logging.INFO.

        If no options are provided, default values will be used.
        """
        if opts is None:
            opts = {}

        # Set up logging
        self.logger = opts.get("logger")
        if self.logger is None:
            log_level = opts.get("log_level", logging.INFO)
            self.logger = self._setup_logger(log_level)

        # In Python 3.9, we can't directly annotate Queue with a type var
        # so we use a comment annotation instead
        self.work_queue = queue.Queue()  # type: queue.Queue[T]
        self.thread_mutex: threading.Lock = threading.Lock()
        self.total_executions: int = 0
        self.current_executors: int = 0

        for item in opts.get("work_params", []):
            self.work_queue.put(item)
        self.max_executions: int = self.work_queue.qsize()

        self.max_threads: int = opts.get("max_threads", self.DEFAULT_MAX_THREADS)

        self.output: bool = opts.get("output_status", self.max_executions > 1)

        self.progress_bar_title: Optional[str] = opts.get("progress_bar_title")
        self.progress_bar: Optional[tqdm] = (
            tqdm(total=self.max_executions, desc=self.progress_bar_title)
            if self.progress_bar_title
            else None
        )

        self.update_seconds: int = opts.get("update_seconds", 60) * 2  # sleeping for 0.5
        self.queue_timeout: Optional[float] = opts.get("queue_timeout", None)

        self.logger.debug("ThreadManager initialized with %d tasks and %d threads",
                          self.max_executions, self.max_threads)

    def run(self, func: Callable[[T], None]) -> None:
        """
        Executes tasks from the work queue using multiple threads.

        Args:
            func (callable): The function to be executed for each task in the work queue.

        The method continuously checks the work queue and starts new threads to execute the tasks
        until all tasks are completed. It also updates the progress bar and logs the status if enabled.

        Attributes:
            total_loops (int): The total number of loops executed in the while loop.

        The method performs the following steps:
        1. Checks if the work queue is empty and if all tasks have been executed.
        2. Acquires the thread mutex lock to synchronize thread access.
        3. Starts new threads to execute tasks if the number of active executors is less than the maximum allowed.
        4. Updates the progress bar and logs the status at specified intervals.
        5. Sleeps for 0.5 seconds before the next iteration.

        The method exits when all tasks are completed and logs the completion status.
        """
        self.logger.info("Starting execution with %d tasks", self.max_executions)
        total_loops = 0

        while True:
            if self.work_queue.empty() and self.total_executions == self.max_executions:
                break

            with self.thread_mutex:
                while (
                    self.current_executors < self.max_threads
                    and not self.work_queue.empty()
                ):
                    thread_name = f"Worker-{self.current_executors}"
                    thread = threading.Thread(
                        target=self._worker,
                        args=(func,),
                        name=thread_name
                    )
                    thread.daemon = True  # Make threads daemon so they exit when main thread exits
                    thread.start()
                    self.current_executors += 1
                    self.logger.debug("Started thread %s", thread_name)

            total_loops += 1
            if self.progress_bar:
                self.progress_bar.n = self.total_executions
                self.progress_bar.refresh()

            if self.output and total_loops % self.update_seconds == 0:
                self.logger.info(
                    "Completed %d out of %d hosts",
                    self.total_executions, self.max_executions
                )

            time.sleep(0.5)

        if self.progress_bar:
            self.progress_bar.update(self.max_executions - self.progress_bar.n)
            self.progress_bar.close()
        if self.output:
            self.logger.info("Execution is complete")

    def _worker(self, func: Callable[[T], None]) -> None:
        """
        Executes a single task from the work queue.

        Args:
            func (callable): The function to be executed for the task.

        The method retrieves a task from the work queue and executes the provided function with the task as an argument.
        It ensures that the total number of executions and the current number of active executors are updated correctly
        using a mutex lock to synchronize access.

        The method performs the following steps:
        1. Retrieves a task from the work queue with an optional timeout.
        2. Executes the provided function with the task.
        3. Increments the total number of executions.
        4. Decrements the current number of active executors.
        5. Handles and logs any exceptions that may occur during task execution.
        """
        task = None
        try:
            try:
                task = self.work_queue.get(timeout=self.queue_timeout)
                func(task)
            except queue.Empty:
                if self.output:
                    self.logger.debug("Queue get operation timed out")
                return
        except Exception as e:  # pylint: disable=broad-except
            if self.output:
                self.logger.error("Error executing task: %s", str(e), exc_info=True)
        finally:
            # Mark the task as done regardless of success or failure
            if task is not None:
                self.work_queue.task_done()

            with self.thread_mutex:
                self.total_executions += 1
                self.current_executors -= 1

    def _setup_logger(self, log_level: int = logging.INFO) -> logging.Logger:
        """
        Set up a logger with the given log level.

        Args:
            log_level (int): The log level for the logger.

        Returns:
            logging.Logger: A configured logger instance.
        """
        logger = logging.getLogger(f"threadman.{id(self)}")
        logger.setLevel(log_level)

        # Create a console handler if there isn't one already
        if not logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(log_level)

            # Create a formatter
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(formatter)

            # Add the handler to the logger
            logger.addHandler(console_handler)

        return logger
