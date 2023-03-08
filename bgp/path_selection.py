#!/usr/bin/env python3
"""
BGP Best Path Selection Algorithm

Implements the decision process routers use to select the best
route when multiple paths exist to the same destination.
"""

class Route:
    """A BGP route with its path attributes."""
    def __init__(self, name, prefix, as_path, next_hop, local_pref=100,
                 origin='i', med=0, source='eBGP', router_id="0.0.0.0"):
        self.name = name  # Friendly name for demo
        self.prefix = prefix
        self.as_path = as_path
        self.next_hop = next_hop
        self.local_pref = local_pref
        self.origin = origin  # 'i'=IGP, 'e'=EGP, '?'=incomplete
        self.med = med
        self.source = source  # 'eBGP' or 'iBGP'
        self.router_id = router_id

    def __repr__(self):
        return self.name

    def summary(self):
        """One-line summary of the route."""
        origin_names = {'i': 'IGP', 'e': 'EGP', '?': 'incomplete'}
        return (f"{self.name}: AS_PATH={self.as_path or '(local)'}, "
                f"LP={self.local_pref}, MED={self.med}, "
                f"origin={origin_names.get(self.origin, self.origin)}, "
                f"via {self.source}")


def get_igp_cost(next_hop):
    """Simulated IGP cost to reach next-hop (OSPF/IS-IS metric)."""
    costs = {
        "192.168.1.1": 10,
        "192.168.1.2": 5,
        "192.168.1.3": 15,
        "0.0.0.0": 0,
    }
    return costs.get(next_hop, 9999)


def select_best_path(routes, verbose=True):
    """
    BGP Best Path Selection Algorithm.

    Returns the single best route from a list of candidates.
    """
    if not routes:
        return None

    def log_step(step_num, criterion, remaining, eliminated=None):
        if not verbose:
            return
        print(f"\n  Step {step_num}: {criterion}")
        if eliminated:
            for r in eliminated:
                print(f"    ✗ {r.name} — eliminated")
        for r in remaining:
            print(f"    ✓ {r.name} — still in")
        if len(remaining) == 1:
            print(f"\n  ══════════════════════════════════════")
            print(f"  ★ WINNER: {remaining[0].name}")
            print(f"  ══════════════════════════════════════")

    candidates = routes[:]
    step = 0

    # --- Step 1: Highest LOCAL_PREF ---
    step += 1
    max_lp = max(r.local_pref for r in candidates)
    eliminated = [r for r in candidates if r.local_pref != max_lp]
    candidates = [r for r in candidates if r.local_pref == max_lp]
    log_step(step, f"Highest LOCAL_PREF (best={max_lp})", candidates, eliminated)
    if len(candidates) == 1:
        return candidates[0]

    # --- Step 2: Locally Originated ---
    step += 1
    local = [r for r in candidates if not r.as_path]
    if local:
        eliminated = [r for r in candidates if r.as_path]
        candidates = local
        log_step(step, "Prefer locally originated (empty AS_PATH)", candidates, eliminated)
        if len(candidates) == 1:
            return candidates[0]
    else:
        if verbose:
            print(f"\n  Step {step}: Locally originated — (no local routes, skip)")

    # --- Step 3: Shortest AS_PATH ---
    step += 1
    min_len = min(len(r.as_path) for r in candidates)
    eliminated = [r for r in candidates if len(r.as_path) != min_len]
    candidates = [r for r in candidates if len(r.as_path) == min_len]
    log_step(step, f"Shortest AS_PATH (best={min_len} hops)", candidates, eliminated)
    if len(candidates) == 1:
        return candidates[0]

    # --- Step 4: Lowest ORIGIN ---
    step += 1
    origin_pref = {'i': 1, 'e': 2, '?': 3}
    origin_names = {'i': 'IGP', 'e': 'EGP', '?': 'incomplete'}
    min_origin = min(origin_pref[r.origin] for r in candidates)
    best_origin = [k for k, v in origin_pref.items() if v == min_origin][0]
    eliminated = [r for r in candidates if origin_pref[r.origin] != min_origin]
    candidates = [r for r in candidates if origin_pref[r.origin] == min_origin]
    log_step(step, f"Lowest ORIGIN (best={origin_names[best_origin]})", candidates, eliminated)
    if len(candidates) == 1:
        return candidates[0]

    # --- Step 5: Lowest MED ---
    step += 1
    min_med = min(r.med for r in candidates)
    eliminated = [r for r in candidates if r.med != min_med]
    candidates = [r for r in candidates if r.med == min_med]
    log_step(step, f"Lowest MED (best={min_med})", candidates, eliminated)
    if len(candidates) == 1:
        return candidates[0]

    # --- Step 6: eBGP over iBGP ---
    step += 1
    ebgp = [r for r in candidates if r.source == 'eBGP']
    if ebgp:
        eliminated = [r for r in candidates if r.source != 'eBGP']
        candidates = ebgp
        log_step(step, "Prefer eBGP over iBGP", candidates, eliminated)
        if len(candidates) == 1:
            return candidates[0]
    else:
        if verbose:
            print(f"\n  Step {step}: eBGP over iBGP — (all same type, skip)")

    # --- Step 7: Lowest IGP cost to next-hop ---
    step += 1
    min_cost = min(get_igp_cost(r.next_hop) for r in candidates)
    eliminated = [r for r in candidates if get_igp_cost(r.next_hop) != min_cost]
    candidates = [r for r in candidates if get_igp_cost(r.next_hop) == min_cost]
    log_step(step, f"Lowest IGP cost to next-hop (best={min_cost})", candidates, eliminated)
    if len(candidates) == 1:
        return candidates[0]

    # --- Step 8: Lowest Router ID ---
    step += 1
    min_rid = min(r.router_id for r in candidates)
    eliminated = [r for r in candidates if r.router_id != min_rid]
    candidates = [r for r in candidates if r.router_id == min_rid]
    log_step(step, f"Lowest Router ID (best={min_rid})", candidates, eliminated)

    return candidates[0]


def demo():
    """Demonstrate the path selection algorithm."""
    print("\n" + "═" * 50)
    print("  BGP BEST PATH SELECTION DEMO")
    print("  Which route wins for 8.8.8.0/24?")
    print("═" * 50)

    # Create competing routes to Google DNS
    routes = [
        Route(
            name="Route A (via AS 65001)",
            prefix="8.8.8.0/24",
            as_path=[65001],
            next_hop="192.168.1.1",
            local_pref=100,
            origin='i',
            med=10,
            source='eBGP',
            router_id="1.1.1.1"
        ),
        Route(
            name="Route B (via AS 65002→65001)",
            prefix="8.8.8.0/24",
            as_path=[65002, 65001],
            next_hop="192.168.1.2",
            local_pref=100,
            origin='i',
            med=5,
            source='eBGP',
            router_id="2.2.2.2"
        ),
        Route(
            name="Route C (via AS 65003)",
            prefix="8.8.8.0/24",
            as_path=[65003],
            next_hop="192.168.1.3",
            local_pref=90,  # Lower preference
            origin='i',
            med=0,
            source='eBGP',
            router_id="3.3.3.3"
        ),
        Route(
            name="Route D (via AS 65004)",
            prefix="8.8.8.0/24",
            as_path=[65004],
            next_hop="192.168.1.1",
            local_pref=100,
            origin='e',  # EGP origin (less preferred than IGP)
            med=10,
            source='eBGP',
            router_id="4.4.4.4"
        ),
    ]

    print("\n  Candidate Routes:")
    print("  " + "─" * 46)
    for r in routes:
        print(f"  • {r.summary()}")
    print("  " + "─" * 46)
    print("\n  Running selection algorithm...")

    winner = select_best_path(routes)

    print(f"\n  Final selection: {winner.name}")
    print(f"  Reason: Shortest AS_PATH (1 hop) + IGP origin")
    print()


if __name__ == "__main__":
    demo()
