from collections import deque


def solve():
    initial = {"remaining": 6, "coins_used": 0}

    def use1(s):
        if not (s["remaining"] >= 1):
            return None
        return {**s, "remaining": s["remaining"] - 1, "coins_used": s["coins_used"] + 1}

    def use3(s):
        if not (s["remaining"] >= 3):
            return None
        return {**s, "remaining": s["remaining"] - 3, "coins_used": s["coins_used"] + 1}

    def use4(s):
        if not (s["remaining"] >= 4):
            return None
        return {**s, "remaining": s["remaining"] - 4, "coins_used": s["coins_used"] + 1}

    all_actions = [
        ("Use1", use1),
        ("Use3", use3),
        ("Use4", use4),
    ]

    def is_valid(s):
        return 0 <= s["remaining"] <= 6 and 0 <= s["coins_used"] <= 6

    def is_goal(s):
        return s["remaining"] == 0

    queue = deque([(initial, [])])
    visited = {tuple(sorted(initial.items()))}

    while queue:
        state, path = queue.popleft()
        if is_goal(state):
            print(f"Solution found in {len(path)} steps:\n")
            desc = ", ".join(f"{k}={v}" for k, v in sorted(initial.items()))
            print(f"  Start: {desc}")
            for action_name, result in path:
                desc = ", ".join(f"{k}={v}" for k, v in sorted(result.items()))
                print(f"  {action_name} -> {desc}")
            return

        for action_name, action_fn in all_actions:
            next_state = action_fn(state)
            if next_state is None:
                continue
            key = tuple(sorted(next_state.items()))
            if key not in visited and is_valid(next_state):
                visited.add(key)
                queue.append((next_state, path + [(action_name, next_state)]))

    print("No solution found")


solve()
