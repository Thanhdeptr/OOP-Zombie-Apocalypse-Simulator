

import math


class Object:
    def __init__(self, id: int, type: int, x: int, y: int, s: int):
        self.id = id
        self.type = type
        self.x = x
        self.y = y
        self.s = s


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



class Citizen(Object):
    def __init__(self, id: int, type: int, x: int, y: int, s: int, vision: int):
        super().__init__(id, 2, x, y, s)
        self.v = vision

    def run(self, zombie_array: list["Zombie"]) -> int:
        # 0: no zombie in vision, 1: moved
        if not zombie_array:
            return 0

        nearest: Zombie | None = None
        best_dist2: int | None = None
        vision2 = self.v * self.v

        # Find nearest zombie inside citizen vision.
        for z in zombie_array:
            dist2 = (z.x - self.x) ** 2 + (z.y - self.y) ** 2
            if dist2 <= vision2 and (best_dist2 is None or dist2 < best_dist2):
                best_dist2 = dist2
                nearest = z

        if nearest is None:
            return 0

        # Move one step away from nearest zombie (diagonal or straight).
        dx = self.x - nearest.x
        dy = self.y - nearest.y
        step_x = 0 if dx == 0 else (1 if dx > 0 else -1)
        step_y = 0 if dy == 0 else (1 if dy > 0 else -1)

        self.x = min(19, max(0, self.x + step_x))
        self.y = min(19, max(0, self.y + step_y))
        return 1


class Zombie(Object):
    def __init__(self, id: int, type: int, x: int, y: int, s: int):
        super().__init__(id, 3, x, y, s)

    def hunt(
        self,
        human_array: list[Soldier | Citizen],
        pending_infected: list[tuple[int, int, int, int]],
        pending_human_ids: set[int],
    ) -> int:
        # 0: no target, 1: moved, 2: infected target
        if not human_array:
            return 0

        # Find nearest target with squared distance (faster than sqrt).
        target_idx = -1
        best_dist2: int | None = None
        for i in range(len(human_array)):
            if human_array[i].id in pending_human_ids:
                continue
            h = human_array[i]
            dist2 = (h.x - self.x) ** 2 + (h.y - self.y) ** 2
            if best_dist2 is None or dist2 < best_dist2:
                best_dist2 = dist2
                target_idx = i

        if target_idx == -1:
            return 0

        target = human_array[target_idx]
        dx = target.x - self.x
        dy = target.y - self.y

        # If target is in neighboring area (Chebyshev distance <= 1), infect now.
        if abs(dx) <= 1 and abs(dy) <= 1:
            # Store snapshot of victim data for next-turn conversion.
            pending_infected.append((target.id, target.x, target.y, target.s))
            pending_human_ids.add(target.id)
            return 2

        # Move exactly one step toward target (diagonal or straight).
        step_x = 0 if dx == 0 else (1 if dx > 0 else -1)
        step_y = 0 if dy == 0 else (1 if dy > 0 else -1)
        self.x += step_x
        self.y += step_y
        return 1


def _read_n_m() -> tuple[int, int]:
    while True:
        line = input().strip()
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
        line = input(f"Nhap ca the thu {i + 1}: ").strip()
        if not line:
            print("Dong trong. Vui long nhap lai.")
            continue
        return line.split()


def get_input_data():
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

    while turn < m and human_array:
        turn += 1

        # Apply infections from previous turn:
        # - pop humans by recorded indexes
        # - convert them into zombies now (deferred infection)
        new_zombies: list[Zombie] = []
        if pending_infected:
            # Remove humans that were marked infected in previous turn.
            pending_ids = {pid for pid, _, _, _ in pending_infected}
            human_array = [h for h in human_array if h.id not in pending_ids]

            # Convert victims to zombies using stored snapshot (id, x, y, s).
            for pid, px, py, ps in pending_infected:
                new_zombies.append(Zombie(pid, 3, px, py, ps))
            zombie_array.extend(new_zombies)

            pending_infected.clear()
            pending_human_ids.clear()

        # Citizens run first.
        for h in human_array:
            if isinstance(h, Citizen):
                h.run(zombie_array)

        # Soldiers attack after citizens move.
        for h in human_array:
            if isinstance(h, Soldier):
                h.attack(zombie_array)

        # Zombies hunt and may infect humans.
        current_zombies = list(zombie_array)
        for z in current_zombies:
            z.hunt(human_array, pending_infected, pending_human_ids)

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
