from collections.abc import Callable


def occupied_cells(
    human_array: list,
    zombie_array: list,
    exclude_id: int,
) -> set[tuple[int, int]]:
    cells: set[tuple[int, int]] = set()
    for h in human_array:
        if h.id != exclude_id and 0 <= h.x < 20 and 0 <= h.y < 20:
            cells.add((h.x, h.y))
    for z in zombie_array:
        if z.id != exclude_id and 0 <= z.x < 20 and 0 <= z.y < 20:
            cells.add((z.x, z.y))
    return cells


def pick_step_with_wall_slide(
    x: int,
    y: int,
    step_x: int,
    step_y: int,
    occupied: set[tuple[int, int]],
    score: Callable[[int, int], int],
    *,
    maximize: bool,
) -> tuple[int, int] | None:
    """
    Prefer one step (step_x, step_y). If out of map or cell taken, pick the best
    legal king-move (including sliding along the wall) by score.
    """
    px, py = x + step_x, y + step_y
    if 0 <= px < 20 and 0 <= py < 20 and (px, py) not in occupied:
        return px, py

    candidates: list[tuple[int, int]] = []

    tx = min(19, max(0, x + step_x))
    if (tx, y) != (x, y) and 0 <= tx < 20 and (tx, y) not in occupied:
        candidates.append((tx, y))

    ty = min(19, max(0, y + step_y))
    if (x, ty) != (x, y) and 0 <= ty < 20 and (x, ty) not in occupied:
        candidates.append((x, ty))

    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            nx, ny = x + dx, y + dy
            if 0 <= nx < 20 and 0 <= ny < 20 and (nx, ny) not in occupied:
                candidates.append((nx, ny))

    if not candidates:
        return None

    if maximize:
        return max(candidates, key=lambda p: score(p[0], p[1]))
    return min(candidates, key=lambda p: score(p[0], p[1]))
