"""
Laya Creative Window Layout Organizer
Dynamically organizes and tiles open desktop windows into intelligent geometric layouts:
Grid, Side-by-Side (Split), Triple Column, Golden Ratio, Cascade, Cinema Focus, and Creative Dashboard.
"""

import time
import win32gui
import win32con
from typing import List, Dict, Any, Optional, Tuple

from laya.tools.win32_utils import (
    ensure_desktop_access,
    get_desktop_work_area,
    get_open_windows,
    robust_bring_to_front,
)


class WindowOrganizer:
    _instance: Optional["WindowOrganizer"] = None

    @classmethod
    def get_instance(cls) -> "WindowOrganizer":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _get_target_windows(self, target_apps: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get visible application windows, optionally filtered by application names."""
        ensure_desktop_access()
        all_wins = get_open_windows(min_size=(120, 120))

        # Filter out HUD or desktop overlay windows
        filtered = [
            w for w in all_wins
            if not any(ign in w["title"].lower() for ign in ["laya hud", "antigravity ide -", "geforce overlay"])
        ]

        if not filtered and all_wins:
            filtered = all_wins

        if not target_apps:
            return filtered

        matched = []
        for app in target_apps:
            a_low = app.lower().strip()
            for w in all_wins:
                if a_low in w["title"].lower() and w not in matched:
                    matched.append(w)
                    break
        return matched if matched else filtered

    def organize(
        self,
        layout: str = "grid",
        target_apps: Optional[List[str]] = None,
        padding: int = 4,
    ) -> str:
        """
        Organize desktop windows into a specified geometric layout.
        Supported layouts:
        - 'grid': 2x2 or NxM balanced tile grid
        - 'split' / 'side_by_side': 50/50 horizontal split
        - 'columns' / 'triple_column': 3-column dashboard (e.g. Code, Browser, Notes)
        - 'golden_ratio': 62% primary window on left, stacked secondary windows on right
        - 'cascade': Diagonal staggered overlap
        - 'focus' / 'cinema': Primary window centered at 80%, other windows minimized
        - 'corners': 4 corners quadrant layout
        - 'creative': Chooses the best aesthetic arrangement based on active window count
        """
        windows = self._get_target_windows(target_apps)
        if not windows:
            return "No active desktop windows found to organize."

        left, top, right, bottom = get_desktop_work_area()
        screen_w = right - left
        screen_h = bottom - top

        clean_layout = layout.lower().strip().replace("-", "_").replace(" ", "_")

        # Automatic creative layout selection based on window count
        if clean_layout in ["creative", "auto", "smart", "shape", "some_shape"]:
            count = len(windows)
            if count == 1:
                clean_layout = "focus"
            elif count == 2:
                clean_layout = "split"
            elif count == 3:
                clean_layout = "golden_ratio"
            elif count == 4:
                clean_layout = "grid"
            else:
                clean_layout = "grid"

        slots: List[Tuple[int, int, int, int]] = []  # (x, y, w, h)

        # -------------------------------------------------------------
        # 1. Side-by-Side / Split (50/50)
        # -------------------------------------------------------------
        if clean_layout in ["split", "side_by_side", "halves", "dual"]:
            half_w = (screen_w - padding * 3) // 2
            h = screen_h - padding * 2
            slots.append((left + padding, top + padding, half_w, h))
            slots.append((left + half_w + padding * 2, top + padding, half_w, h))

        # -------------------------------------------------------------
        # 2. Triple Column / Coding Dashboard (33% / 34% / 33%)
        # -------------------------------------------------------------
        elif clean_layout in ["columns", "triple_column", "three_columns", "3_columns"]:
            col_w = (screen_w - padding * 4) // 3
            h = screen_h - padding * 2
            for i in range(3):
                slots.append((left + padding + i * (col_w + padding), top + padding, col_w, h))

        # -------------------------------------------------------------
        # 3. Golden Ratio / Developer Focus (62% primary + stacked right)
        # -------------------------------------------------------------
        elif clean_layout in ["golden_ratio", "master_stack", "dev_focus"]:
            primary_w = int((screen_w - padding * 3) * 0.62)
            secondary_w = screen_w - primary_w - padding * 3
            full_h = screen_h - padding * 2

            slots.append((left + padding, top + padding, primary_w, full_h))

            remaining_wins = max(1, len(windows) - 1)
            slot_h = (full_h - padding * (remaining_wins - 1)) // remaining_wins
            for i in range(remaining_wins):
                slots.append((
                    left + primary_w + padding * 2,
                    top + padding + i * (slot_h + padding),
                    secondary_w,
                    slot_h,
                ))

        # -------------------------------------------------------------
        # 4. Cascade (Diagonal Staggered)
        # -------------------------------------------------------------
        elif clean_layout in ["cascade", "staggered", "diagonal"]:
            win_w = int(screen_w * 0.70)
            win_h = int(screen_h * 0.75)
            step_x = 45
            step_y = 40
            for i in range(len(windows)):
                cx = left + padding + (i * step_x) % (screen_w - win_w)
                cy = top + padding + (i * step_y) % (screen_h - win_h)
                slots.append((cx, cy, win_w, win_h))

        # -------------------------------------------------------------
        # 5. Focus / Cinema Mode (Center 80%, minimize remainder)
        # -------------------------------------------------------------
        elif clean_layout in ["focus", "cinema", "center"]:
            f_w = int(screen_w * 0.80)
            f_h = int(screen_h * 0.85)
            c_x = left + (screen_w - f_w) // 2
            c_y = top + (screen_h - f_h) // 2
            slots.append((c_x, c_y, f_w, f_h))

            # Minimize any background windows past the primary
            for w in windows[1:]:
                try:
                    win32gui.ShowWindow(w["hwnd"], win32con.SW_MINIMIZE)
                except Exception:
                    pass

        # -------------------------------------------------------------
        # 6. Corners (4 Quadrants) or Balanced Grid
        # -------------------------------------------------------------
        elif clean_layout in ["corners", "quad"]:
            half_w = (screen_w - padding * 3) // 2
            half_h = (screen_h - padding * 3) // 2
            slots = [
                (left + padding, top + padding, half_w, half_h),                              # Top-Left
                (left + half_w + padding * 2, top + padding, half_w, half_h),                 # Top-Right
                (left + padding, top + half_h + padding * 2, half_w, half_h),                 # Bottom-Left
                (left + half_w + padding * 2, top + half_h + padding * 2, half_w, half_h),    # Bottom-Right
            ]

        # -------------------------------------------------------------
        # 7. Balanced Default Grid (NxM)
        # -------------------------------------------------------------
        else:  # "grid"
            n = len(windows)
            if n <= 1:
                cols, rows = 1, 1
            elif n == 2:
                cols, rows = 2, 1
            elif n <= 4:
                cols, rows = 2, 2
            elif n <= 6:
                cols, rows = 3, 2
            else:
                cols, rows = 3, 3

            cell_w = (screen_w - padding * (cols + 1)) // cols
            cell_h = (screen_h - padding * (rows + 1)) // rows

            for r in range(rows):
                for c in range(cols):
                    slots.append((
                        left + padding + c * (cell_w + padding),
                        top + padding + r * (cell_h + padding),
                        cell_w,
                        cell_h,
                    ))

        # Position the windows into the computed geometric slots
        positioned_count = 0
        positioned_titles = []

        for i, win in enumerate(windows):
            if i >= len(slots):
                break
            hwnd = win["hwnd"]
            x, y, w, h = slots[i]
            try:
                # Restore window if minimized or maximized
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                time.sleep(0.01)
                win32gui.SetWindowPos(
                    hwnd,
                    win32con.HWND_TOP,
                    int(x),
                    int(y),
                    int(w),
                    int(h),
                    win32con.SWP_SHOWWINDOW,
                )
                positioned_count += 1
                positioned_titles.append(f"'{win['title'][:25]}'")
            except Exception as e:
                print(f"[WindowOrganizer] MoveWindow failed on {win['title']}: {e}")

        # Bring the primary window to the front
        if windows:
            robust_bring_to_front(windows[0]["hwnd"])

        summary_titles = ", ".join(positioned_titles[:4])
        return f"Organized {positioned_count} windows into a {clean_layout} layout ({summary_titles})."


def get_window_organizer() -> WindowOrganizer:
    return WindowOrganizer.get_instance()
