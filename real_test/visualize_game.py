import time

from zombie_apocalypse_oop import Citizen, Soldier, Zombie, get_input_data


# ANSI colors for terminal rendering.
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"
CLEAR = "\033[2J\033[H"


def build_map(human_array: list[Soldier | Citizen], zombie_array: list[Zombie]) -> list[list[int | None]]:
    """Build a 20x20 map from current entity positions."""
    game_map: list[list[int | None]] = [[None for _ in range(20)] for _ in range(20)]

    for h in human_array:
        if 0 <= h.x < 20 and 0 <= h.y < 20:
            game_map[h.y][h.x] = h.type

    for z in zombie_array:
        if 0 <= z.x < 20 and 0 <= z.y < 20:
            game_map[z.y][z.x] = z.type

    return game_map


def render_map(game_map: list[list[int | None]], turn: int, human_count: int, zombie_count: int) -> None:
    """Render map with colored symbols."""
    print(CLEAR, end="")
    print(f"Turn {turn} | Humans={human_count} | Zombies={zombie_count}")
    print(f"Legend: {GREEN}1{RESET}=Soldier  {YELLOW}2{RESET}=Citizen  {RED}3{RESET}=Zombie  .=Empty")
    print("   " + " ".join(f"{i:02d}" for i in range(20)))

    for y in range(20):
        row_out: list[str] = []
        for x in range(20):
            cell = game_map[y][x]
            if cell is None:
                row_out.append(". ")
            elif cell == 1:
                row_out.append(f"{GREEN}1{RESET} ")
            elif cell == 2:
                row_out.append(f"{YELLOW}2{RESET} ")
            elif cell == 3:
                row_out.append(f"{RED}3{RESET} ")
            else:
                row_out.append("? ")
        print(f"{y:02d} " + "".join(row_out))


def main() -> None:
    _, turn, _, m, _, human_array, zombie_array = get_input_data()

    # Deferred infection storage:
    # (id, x, y, speed) of infected human snapshots.
    pending_infected: list[tuple[int, int, int, int]] = []
    pending_human_ids: set[int] = set()

    # Show initial state before any action.
    initial_map = build_map(human_array, zombie_array)
    render_map(initial_map, turn, len(human_array), len(zombie_array))
    time.sleep(1.5)

    while turn < m and (human_array or zombie_array):
        turn += 1

        # Apply infections from previous turn.
        new_zombies: list[Zombie] = []
        if pending_infected:
            pending_ids = {pid for pid, _, _, _ in pending_infected}
            human_array = [h for h in human_array if h.id not in pending_ids]
            for pid, px, py, ps in pending_infected:
                new_zombies.append(Zombie(pid, 3, px, py, ps))
            zombie_array.extend(new_zombies)
            pending_infected.clear()
            pending_human_ids.clear()

        # 1) Citizens run.
        for h in human_array:
            if isinstance(h, Citizen):
                h.run(zombie_array)

        # 2) Soldiers attack.
        for h in human_array:
            if isinstance(h, Soldier):
                h.attack(zombie_array)

        # 3) Zombies hunt.
        for z in list(zombie_array):
            z.hunt(human_array, pending_infected, pending_human_ids)

        current_map = build_map(human_array, zombie_array)
        render_map(current_map, turn, len(human_array), len(zombie_array))
        time.sleep(1.5)

    print("\nSimulation ended.")
    soldier_count = sum(1 for h in human_array if isinstance(h, Soldier))
    citizen_count = sum(1 for h in human_array if isinstance(h, Citizen))
    zombie_count = len(zombie_array)
    print(
        f"Final counts -> Zombie: {zombie_count}, "
        f"Soldier: {soldier_count}, Citizen: {citizen_count}"
    )


if __name__ == "__main__":
    main()
