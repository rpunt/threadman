# threadman

A simple, type-annotated thread manager for Python. Easily manage and execute tasks concurrently using a configurable thread pool, with progress bar and logging support.

## Features

- Simple API for concurrent task execution
- Configurable thread pool size
- Progress bar (via `tqdm`)
- Logging support (uses Python's `logging` module)
- Type annotations for better IDE and type checker support

## Installation

```bash
pip install threadman
```

Or install from source:

```bash
git clone https://github.com/your-username/threadman.git
cd threadman
uv build
pip install dist/threadman-*.whl
```

## Usage Example

```python
from threadman import ThreadManager

def my_task(item):
    print(f"Processing {item}")

items = [1, 2, 3, 4, 5]
opts = {
    "work_params": items,
    "max_threads": 3,
    "progress_bar_title": "Processing Items",
    "output_status": True,
}

manager = ThreadManager(opts)
manager.run(my_task)
```

## Options

- `work_params`: List of tasks to execute
- `max_threads`: Maximum number of concurrent threads (default: 10)
- `progress_bar_title`: Title for the progress bar (optional)
- `output_status`: Enable logging/progress output (default: True if more than one task)
- `update_seconds`: Progress/log update interval (default: 60)
- `queue_timeout`: Timeout for queue operations (default: None)

## License

MIT

---

For more details, see the code and docstrings in the `threadman` package.
