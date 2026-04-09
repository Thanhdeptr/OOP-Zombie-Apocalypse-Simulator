

import math
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from io_utils import is_file_input_mode, read_line, reset_input_from_argv
from movement_utils import occupied_cells, pick_step_with_wall_slide


class Phase(str, Enum):
    CITIZEN_MOVE = "citizen_move"
    SOLDIER_ATTACK = "soldier_attack"
    ZOMBIE_HUNT = "zombie_hunt"


@dataclass
class GameContext:
    human_array: list
    zombie_array: list
    pending_infected: list[tuple[int, int, int, int]]
    pending_human_ids: set[int]


class Object:
    def __init__(self, id: int, type: int, x: int, y: int, s: int):
        self.id = id
        self.type = type
        self.x = x
        self.y = y
        self.s = s
        self._alive = True

    def is_alive(self) -> bool:
        return self._alive

    def mark_dead(self) -> None:
        self._alive = False

    def try_move(
        self,
        human_array: list,
        zombie_array: list,
        step_x: int,
        step_y: int,
        score: Callable[[int, int], int],
        *,
        maximize: bool,
    ) -> bool:
        occupied = occupied_cells(human_array, zombie_array, self.id)
        chosen = pick_step_with_wall_slide(
            self.x, self.y, step_x, step_y, occupied, score, maximize=maximize
        )
        if chosen is None:
            return False
        self.x, self.y = chosen
        return True

    def take_turn(self, phase: Phase, ctx: GameContext) -> int:
        # Default: this entity does not act in this phase.
        return 0


class Soldier(Object):
    def __init__(self, id: int, type: int, x: int, y: int, level: int):
        super().__init__(id, 1, x, y, 1)
        self.lvl = level
        self.RNG = self.lvl
        self.AD = self.lvl
    
    def attack(self, zombie_array: list["Zombie"]) -> int:
        in_range_indexes: list[int] = []

        for i, z in enumerate(zombie_array):
            distance = math.sqrt((z.x - self.x) ** 2 + (z.y - self.y) ** 2)
            if distance <= self.RNG:
                in_range_indexes.append(i)

        if not in_range_indexes:
            return 0

        kill_count = min(self.AD, len(in_range_indexes))

        for idx in reversed(in_range_indexes[:kill_count]):
            del zombie_array[idx]

        return kill_count

    def take_turn(self, phase: Phase, ctx: GameContext) -> int:
        if phase == Phase.SOLDIER_ATTACK:
            return self.attack(ctx.zombie_array)
        return 0



class Citizen(Object):
    def __init__(self, id: int, type: int, x: int, y: int, s: int, vision: int):
        super().__init__(id, 2, x, y, s)
        self.v = vision

    def run(self, human_array: list, zombie_array: list["Zombie"]) -> int:
        # 0: no zombie in vision or no legal step, 1: moved
        # Cannot step onto another human or any zombie (_occupied_cells).
        if not zombie_array:
            return 0

        vision2 = self.v * self.v

        def nearest_zombie_in_vision() -> "Zombie | None":
            best: Zombie | None = None
            best_d2: int | None = None
            for z in zombie_array:
                d2 = (z.x - self.x) ** 2 + (z.y - self.y) ** 2
                if d2 <= vision2 and (best_d2 is None or d2 < best_d2):
                    best_d2 = d2
                    best = z
            return best

        moves = max(0, self.s)
        if moves == 0:
            return 0

        moved_any = False
        for _ in range(moves):
            nearest = nearest_zombie_in_vision()
            if nearest is None:
                break

            dx = self.x - nearest.x
            dy = self.y - nearest.y
            step_x = 0 if dx == 0 else (1 if dx > 0 else -1)
            step_y = 0 if dy == 0 else (1 if dy > 0 else -1)

            def score_flee(nx: int, ny: int, zz: Zombie = nearest) -> int:
                return (nx - zz.x) ** 2 + (ny - zz.y) ** 2

            moved = self.try_move(
                human_array,
                zombie_array,
                step_x,
                step_y,
                score_flee,
                maximize=True,
            )
            if not moved:
                break
            moved_any = True

        return 1 if moved_any else 0

    def take_turn(self, phase: Phase, ctx: GameContext) -> int:
        if phase == Phase.CITIZEN_MOVE:
            return self.run(ctx.human_array, ctx.zombie_array)
        return 0


class Zombie(Object):
    def __init__(self, id: int, type: int, x: int, y: int, s: int):
        super().__init__(id, 3, x, y, s)

    def hunt(
        self,
        human_array: list,
        zombie_array: list["Zombie"],
        pending_infected: list[tuple[int, int, int, int]],
        pending_human_ids: set[int],
    ) -> int:
        # 0: no target, 1: moved, 2: infected target
        # Humans run before zombies this turn; zombie never enters a human cell
        # (_occupied_cells), so positions cannot overlap after a legal move.
        if not human_array:
            return 0

        # Among soldiers with Euclidean distance <= self.s, prefer higher lvl;
        # tie-break by smaller distance. Otherwise fall back to nearest human (any type).
        s2 = self.s * self.s

        def nearest_target() -> tuple[int, Soldier | Citizen] | None:
            candidates: list[tuple[int, Soldier | Citizen, int]] = []
            for i in range(len(human_array)):
                if human_array[i].id in pending_human_ids:
                    continue
                h = human_array[i]
                d2 = (h.x - self.x) ** 2 + (h.y - self.y) ** 2
                candidates.append((i, h, d2))
            if not candidates:
                return None

            soldiers_in_range: list[tuple[int, Soldier, int]] = []
            for i, h, d2 in candidates:
                if isinstance(h, Soldier) and d2 <= s2:
                    soldiers_in_range.append((i, h, d2))

            if soldiers_in_range:
                best_i, best_h, _ = max(
                    soldiers_in_range, key=lambda t: (t[1].lvl, -t[2])
                )
                return best_i, best_h

            best_i, best_h, _ = min(candidates, key=lambda t: t[2])
            return best_i, best_h

        nt = nearest_target()
        if nt is None:
            return 0
        _, t0 = nt
        dx0 = t0.x - self.x
        dy0 = t0.y - self.y
        if abs(dx0) <= 1 and abs(dy0) <= 1:
            pending_infected.append((t0.id, t0.x, t0.y, t0.s))
            pending_human_ids.add(t0.id)
            return 2

        moves = max(0, self.s)
        if moves == 0:
            return 0

        moved_any = False
        for _ in range(moves):
            nt = nearest_target()
            if nt is None:
                break
            _, target = nt

            dx = target.x - self.x
            dy = target.y - self.y
            if abs(dx) <= 1 and abs(dy) <= 1:
                pending_infected.append((target.id, target.x, target.y, target.s))
                pending_human_ids.add(target.id)
                return 2

            step_x = 0 if dx == 0 else (1 if dx > 0 else -1)
            step_y = 0 if dy == 0 else (1 if dy > 0 else -1)

            def score_chase(nx: int, ny: int, tt: Soldier | Citizen = target) -> int:
                return (nx - tt.x) ** 2 + (ny - tt.y) ** 2

            moved = self.try_move(
                human_array,
                zombie_array,
                step_x,
                step_y,
                score_chase,
                maximize=False,
            )
            if not moved:
                break
            moved_any = True

        return 1 if moved_any else 0

    def take_turn(self, phase: Phase, ctx: GameContext) -> int:
        if phase == Phase.ZOMBIE_HUNT:
            return self.hunt(
                ctx.human_array,
                ctx.zombie_array,
                ctx.pending_infected,
                ctx.pending_human_ids,
            )
        return 0


def _read_n_m() -> tuple[int, int]:
    while True:
        line = read_line().strip()
        parts = line.split()
        if len(parts) != 2:
            print("Nhap sai. Dung dinh dang: [n] [m] (2 so nguyen). Vi du: 3 10")
            continue
        try:
            n = int(parts[0])
            m = int(parts[1])
        except ValueError:
            print("Nhap sai. [n] va [m] phai la so nguyen. Vi du: 3 10")
            continue
        if n < 0 or m < 0:
            print("Nhap sai. [n] va [m] phai >= 0. Vi du: 3 10")
            continue
        return n, m


def _read_entity_line(i: int) -> list[str]:
    while True:
        line = read_line(f"Nhap ca the thu {i + 1}: ").strip()
        if not line:
            if is_file_input_mode():
                raise ValueError(
                    f"Dong trong trong file input (ca the thu {i + 1}). Kiem tra file."
                )
            print("Dong trong. Vui long nhap lai.")
            continue
        return line.split()


def get_input_data():
    reset_input_from_argv()

    # Map 20x20
    game_map: list[list[int | None]] = [[None for _ in range(20)] for _ in range(20)]
    turn = 0

    print("Nhap [n] [m] (so ca the, so luot). Vi du: 3 10")
    n, m = _read_n_m()

    print(
        "Nhap thong tin n ca the (moi dong 1 ca the):\n"
        "Chu y: ID se tu dong tang 1,2,3,... theo thu tu dong nhap (ban KHONG can nhap ID)\n"
        "- Soldier (Type=1): [1] [x] [y] [lvl]\n"
        "- Citizen (Type=2): [2] [x] [y] [speed] [vision]\n"
        "- Zombie  (Type=3): [3] [x] [y] [speed]\n"
        "Quy uoc: 0 <= x,y <= 19"
    )

    zombie_array: list[Zombie] = []
    human_array: list[Soldier | Citizen] = []
    objects: list[Object] = []
    next_id = 1

    idx = 0
    while idx < n:
        parts = _read_entity_line(idx)

        if len(parts) < 3:
            print("Nhap sai. It nhat: [Type] [x] [y]. Nhap lai.")
            continue

        try:
            type_ = int(parts[0])
            x = int(parts[1])
            y = int(parts[2])
        except ValueError:
            print("Nhap sai. [Type] [x] [y] phai la so nguyen. Nhap lai.")
            continue

        id_ = next_id
        next_id += 1

        if type_ not in (1, 2, 3):
            print("Nhap sai. Type chi nhan 1(Soldier), 2(Citizen), 3(Zombie). Nhap lai.")
            continue

        if not (0 <= x < 20 and 0 <= y < 20):
            print("Nhap sai. x,y phai trong [0..19]. Nhap lai.")
            continue

        obj: Object | None = None

        if type_ == 1:
            if len(parts) != 4:
                print("Nhap sai Soldier. Dung: [1] [x] [y] [lvl]. Vi du: 1 3 4 2")
                continue
            try:
                lvl = int(parts[3])
            except ValueError:
                print("Nhap sai Soldier. [lvl] phai la so nguyen. Nhap lai.")
                continue
            obj = Soldier(id_, type_, x, y, lvl)
            human_array.append(obj)
        elif type_ == 2:
            if len(parts) != 5:
                print("Nhap sai Citizen. Dung: [2] [x] [y] [speed] [vision]. Vi du: 2 1 2 2 5")
                continue
            try:
                s = int(parts[3])
                vision = int(parts[4])
            except ValueError:
                print("Nhap sai Citizen. [speed] va [vision] phai la so nguyen. Nhap lai.")
                continue
            obj = Citizen(id_, type_, x, y, s, vision)
            human_array.append(obj)

        else:
            if len(parts) != 4:
                print("Nhap sai Zombie. Dung: [3] [x] [y] [speed]. Vi du: 3 6 7 1")
                continue
            try:
                s = int(parts[3])
            except ValueError:
                print("Nhap sai Zombie. [speed] phai la so nguyen. Nhap lai.")
                continue
            obj = Zombie(id_, type_, x, y, s)
            zombie_array.append(obj)

        # Save
        objects.append(obj)

        if game_map[y][x] is not None:
            print("Canh bao: o (x,y) nay da co object. Van ghi de id tren map.")
        game_map[y][x] = id_

        idx += 1

    return game_map, turn, n, m, objects, human_array, zombie_array


def main():
    game_map, turn, n, m, objects, human_array, zombie_array = get_input_data()
    pending_infected: list[tuple[int, int, int, int]] = []
    pending_human_ids: set[int] = set()
    ctx = GameContext(human_array, zombie_array, pending_infected, pending_human_ids)

    while turn < m and human_array and zombie_array:
        turn += 1

        # Apply infections from previous turn:
        # - pop humans by recorded indexes
        # - convert them into zombies now (deferred infection)
        new_zombies: list[Zombie] = []
        if pending_infected:
            # Remove humans that were marked infected in previous turn.
            pending_ids = {pid for pid, _, _, _ in pending_infected}
            human_array = [h for h in human_array if h.id not in pending_ids]
            ctx.human_array = human_array

            # Convert victims to zombies using stored snapshot (id, x, y, s).
            for pid, px, py, ps in pending_infected:
                new_zombies.append(Zombie(pid, 3, px, py, ps))
            zombie_array.extend(new_zombies)

            pending_infected.clear()
            pending_human_ids.clear()

        # Stop immediately if one side was wiped out (e.g. last human just turned).
        if not human_array or not zombie_array:
            print(f"Turn {turn}: humans={len(human_array)}, zombies={len(zombie_array)}")
            break

        # Citizens run first.
        for h in human_array:
            h.take_turn(Phase.CITIZEN_MOVE, ctx)

        # Soldiers attack after citizens move.
        for h in human_array:
            h.take_turn(Phase.SOLDIER_ATTACK, ctx)

        # Zombies hunt and may infect humans.
        current_zombies = list(zombie_array)
        for z in current_zombies:
            z.take_turn(Phase.ZOMBIE_HUNT, ctx)

        # Rebuild map 20x20 from current living entities.
        game_map = [[None for _ in range(20)] for _ in range(20)]
        for h in human_array:
            if 0 <= h.x < 20 and 0 <= h.y < 20:
                game_map[h.y][h.x] = h.id
        for z in zombie_array:
            if 0 <= z.x < 20 and 0 <= z.y < 20:
                game_map[z.y][z.x] = z.id

        print(f"Turn {turn}: humans={len(human_array)}, zombies={len(zombie_array)}")



if __name__ == "__main__":
    main()
