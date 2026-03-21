# LED Display Improvement Log

| Cycle | Improvement |
|-------|-------------|
| 1 | Add background color support (bg_color in config/renderer) — fills 11px height with color behind text |
| 2 | Compute Y offset from font height for true vertical centering + merge clear/bg into single _clear_with_color operation |
