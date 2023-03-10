#!/usr/bin/env python3
"""BGP Best Path Selection Algorithm."""

class Route:
    """A BGP route with its path attributes."""
    def __init__(self, prefix, as_path, next_hop, local_pref=100,
                 origin='i', med=0, source='eBGP', router_id="0.0.0.0"):
        self.prefix = prefix
        self.as_path = as_path
        self.next_hop = next_hop
        self.local_pref = local_pref
        self.origin = origin  # 'i'=IGP, 'e'=EGP, '?'=incomplete
        self.med = med
        self.source = source  # 'eBGP' or 'iBGP'
        self.router_id = router_id

    def __repr__(self):
        return (f"Route(prefix={self.prefix}, as_path={self.as_path}, "
                f"lp={self.local_pref}, med={self.med}, origin={self.origin}, "
                f"src={self.source}, rid={self.router_id})")


def get_igp_cost(next_hop):
    """Simulated IGP cost to reach next-hop."""
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

    Decision process (RFC 4271):
    1. Highest LOCAL_PREF
    2. Locally originated (empty AS_PATH)
    3. Shortest AS_PATH
    4. Lowest ORIGIN (IGP < EGP < incomplete)
    5. Lowest MED
    6. eBGP over iBGP
    7. Lowest IGP cost to next-hop
    8. Lowest Router ID
    """
    if not routes:
        return None

    def log(msg):
        if verbose:
            print(f"  {msg}")

    candidates = routes[:]

    # Step 1: Highest LOCAL_PREF
    max_lp = max(r.local_pref for r in candidates)
    before = len(candidates)
    candidates = [r for r in candidates if r.local_pref == max_lp]
    log(f"Step 1 (LOCAL_PREF >= {max_lp}): {before} -> {len(candidates)} routes")
    if len(candidates) == 1:
        return candidates[0]

    # Step 2: Locally originated
    local = [r for r in candidates if not r.as_path]
    if local:
        before = len(candidates)
        candidates = local
        log(f"Step 2 (locally originated): {before} -> {len(candidates)} routes")
        if len(candidates) == 1:
            return candidates[0]

    # Step 3: Shortest AS_PATH
    min_len = min(len(r.as_path) for r in candidates)
    before = len(candidates)
    candidates = [r for r in candidates if len(r.as_path) == min_len]
    log(f"Step 3 (AS_PATH len <= {min_len}): {before} -> {len(candidates)} routes")
    if len(candidates) == 1:
        return candidates[0]

    # Step 4: Lowest ORIGIN
    origin_pref = {'i': 1, 'e': 2, '?': 3}
    min_origin = min(origin_pref[r.origin] for r in candidates)
    before = len(candidates)
    candidates = [r for r in candidates if origin_pref[r.origin] == min_origin]
    log(f"Step 4 (ORIGIN = {[k for k,v in origin_pref.items() if v==min_origin][0]}): {before} -> {len(candidates)} routes")
    if len(candidates) == 1:
        return candidates[0]

    # Step 5: Lowest MED
    min_med = min(r.med for r in candidates)
    before = len(candidates)
    candidates = [r for r in candidates if r.med == min_med]
    log(f"Step 5 (MED <= {min_med}): {before} -> {len(candidates)} routes")
    if len(candidates) == 1:
        return candidates[0]

    # Step 6: eBGP over iBGP
    ebgp = [r for r in candidates if r.source == 'eBGP']
    if ebgp:
        before = len(candidates)
        candidates = ebgp
        log(f"Step 6 (eBGP preferred): {before} -> {len(candidates)} routes")
        if len(candidates) == 1:
            return candidates[0]

    # Step 7: Lowest IGP cost to next-hop
    min_cost = min(get_igp_cost(r.next_hop) for r in candidates)
    before = len(candidates)
    candidates = [r for r in candidates if get_igp_cost(r.next_hop) == min_cost]
    log(f"Step 7 (IGP cost <= {min_cost}): {before} -> {len(candidates)} routes")
    if len(candidates) == 1:
        return candidates[0]

    # Step 8: Lowest Router ID (tie-breaker)
    min_rid = min(r.router_id for r in candidates)
    before = len(candidates)
    candidates = [r for r in candidates if r.router_id == min_rid]
    log(f"Step 8 (Router ID = {min_rid}): {before} -> {len(candidates)} routes")

    return candidates[0]


def pause():
    input("\n[Press Enter to continue...]")
    print()

if __name__ == "__main__":
    print("=== BGP Best Path Selection Demo ===\n")
    print("Destination: 8.8.8.0/24 (Google DNS)\n")

    routes = [
        Route(
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
            prefix="8.8.8.0/24",
            as_path=[65003],
            next_hop="192.168.1.3",
            local_pref=90,
            origin='i',
            med=0,
            source='eBGP',
            router_id="3.3.3.3"
        ),
        Route(
            prefix="8.8.8.0/24",
            as_path=[65004],
            next_hop="192.168.1.1",
            local_pref=100,
            origin='e',
            med=10,
            source='eBGP',
            router_id="4.4.4.4"
        ),
    ]

    print("Candidate routes:")
    for i, r in enumerate(routes):
        print(f"  [{i+1}] {r}")

    pause()

    print("Running selection algorithm:")
    winner = select_best_path(routes)

    print(f"\nBest path: {winner}")
