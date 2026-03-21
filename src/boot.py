"""MicroPython boot configuration.

This runs before main.py. Keep minimal — only system-level setup.
"""

import gc

# Run garbage collection early to maximize available RAM
gc.collect()
