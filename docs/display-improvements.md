# LED Display Improvement Log

| Cycle | Improvement |
|-------|-------------|
| 1 | Add background color support (bg_color in config/renderer) — fills 11px height with color behind text |
| 2 | Compute Y offset from font height for true vertical centering + merge clear/bg into single _clear_with_color operation |
| 3 | Cache font/layout per-frame: skip set_font when unchanged, pre-calc fixed-mode X position, remove per-frame measure_text |
| 4 | Add optional 1px accent border lines (top/bottom) to visually fill 11px height around 8px text |
| 5 | Use native clear() for black backgrounds instead of draw_rectangle; cache _has_bg flag to skip per-frame tuple comparison |
| 6 | Skip set_pen when pen color unchanged — dirty flag tracks bg/border changes; black bg + no border = 0 set_pen calls per frame |
| 7 | Tighter scroll loop: 20px gap between text end and re-entry instead of full 53px screen width — shorter blank time for short messages |
