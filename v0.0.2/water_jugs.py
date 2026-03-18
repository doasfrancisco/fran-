from collections import deque


def solve():
    initial = {"big": 0, "small": 0}

    def fill_big(s):
        return {**s, "big": 5}

    def fill_small(s):
        return {**s, "small": 3}

    def empty_big(s):
        return {**s, "big": 0}

    def empty_small(s):
        return {**s, "small": 0}

    def pour_small_to_big(s):
        return {**s, "big": min(s["big"] + s["small"], 5), "small": s["small"] - (min(s["big"] + s["small"], 5) - s["big"])}

    def pour_big_to_small(s):
        return {**s, "small": min(s["big"] + s["small"], 3), "big": s["big"] - (min(s["big"] + s["small"], 3) - s["small"])}

    all_actions = [
        ("FillBig", fill_big),
        ("FillSmall", fill_small),
        ("EmptyBig", empty_big),
        ("EmptySmall", empty_small),
        ("PourSmallToBig", pour_small_to_big),
        ("PourBigToSmall", pour_big_to_small),
    ]

    def is_valid(s):
        return 0 <= s["big"] <= 5 and 0 <= s["small"] <= 3

    def is_goal(s):
        return s["big"] == 4

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
