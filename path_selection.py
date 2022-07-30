# path_selection.py

class Route:
    """A simple class to represent a BGP route and its attributes."""
    def __init__(self, prefix, as_path, next_hop, local_pref=100, origin='i', med=0, source='eBGP', router_id="0.0.0.0"):
        self.prefix = prefix
        self.as_path = as_path
        self.next_hop = next_hop
        self.local_pref = local_pref
        self.origin = origin
        self.med = med
        self.source = source # 'eBGP' or 'iBGP'
        self.router_id = router_id # BGP Router ID of the advertising router

    def __repr__(self):
        """Provides a clean string representation of the Route object."""
        return (f"Route(prefix='{self.prefix}', "
                f"as_path={self.as_path}, "
                f"next_hop='{self.next_hop}', "
                f"local_pref={self.local_pref}, "
                f"origin='{self.origin}', "
                f"med={self.med}, "
                f"source='{self.source}', "
                f"router_id='{self.router_id}')")

# Dummy IGP cost function for simulation
def get_igp_cost(next_hop):
    """
    Simulates IGP cost to reach a next_hop.
    In a real router, this would query the IGP routing table.
    """
    # Assign arbitrary costs for demonstration
    if next_hop == "192.168.1.1": return 10
    if next_hop == "192.168.1.2": return 5
    if next_hop == "192.168.1.3": return 15
    if next_hop == "0.0.0.0": return 0 # Locally originated, cost is 0
    return 9999 # High cost for unknown next-hops


def select_best_path(routes):
    """
    Implements the BGP Best Path Selection Algorithm.
    Takes a list of Route objects and returns the single best Route.
    """
    if not routes:
        return None
    
    # --- Step 1: Highest LOCAL_PREF ---
    max_local_pref = max(route.local_pref for route in routes)
    best_paths = [route for route in routes if route.local_pref == max_local_pref]
    
    if len(best_paths) == 1:
        return best_paths[0]
    
    routes = best_paths
    
    # --- Step 2: Locally Originated ---
    locally_originated_paths = [route for route in routes if not route.as_path]
    
    if locally_originated_paths:
        if len(locally_originated_paths) == 1:
            return locally_originated_paths[0]
        routes = locally_originated_paths
    
    # --- Step 3: Shortest AS_PATH ---
    min_as_path_len = min(len(route.as_path) for route in routes)
    best_paths = [route for route in routes if len(route.as_path) == min_as_path_len]

    if len(best_paths) == 1:
        return best_paths[0]
    
    routes = best_paths
    
    # --- Step 4: Lowest ORIGIN Code ---
    origin_preference = {'i': 1, 'e': 2, '?': 3}
    min_origin_value = min(origin_preference[route.origin] for route in routes)
    best_paths = [route for route in routes if origin_preference[route.origin] == min_origin_value]

    if len(best_paths) == 1:
        return best_paths[0]
    
    routes = best_paths
    
    # --- Step 5: Lowest MED ---
    min_med = min(route.med for route in routes)
    best_paths = [route for route in routes if route.med == min_med]

    if len(best_paths) == 1:
        return best_paths[0]
    
    routes = best_paths
    
    # --- Step 6: Prefer eBGP over iBGP paths ---
    ebgp_paths = [route for route in routes if route.source == 'eBGP']
    # ibgp_paths = [route for route in routes if route.source == 'iBGP'] # not needed if we just filter ebgp
    
    if ebgp_paths: # If there are eBGP paths, prefer them
        if len(ebgp_paths) == 1:
            return ebgp_paths[0]
        routes = ebgp_paths # Proceed with tied eBGP paths
    # else, routes already contains only iBGP paths or a mix that didn't prefer ebgp, so we proceed

    # --- Step 7: Lowest IGP Cost to NEXT_HOP ---
    if len(routes) > 1: # Only apply if there are multiple routes left
        min_igp_cost = min(get_igp_cost(route.next_hop) for route in routes)
        best_paths = [route for route in routes if get_igp_cost(route.next_hop) == min_igp_cost]

        if len(best_paths) == 1:
            return best_paths[0]
        routes = best_paths
    
    # --- Step 8: Final Tie-Breakers (Lowest BGP Router ID) ---
    if len(routes) > 1: # If multiple paths remain (tied after all previous steps)
        min_router_id = min(route.router_id for route in routes)
        best_paths = [route for route in routes if route.router_id == min_router_id]
        
        # If there's still a tie after Router ID, we pick the first one (deterministic but arbitrary)
        return best_paths[0]
    
    # If only one path remained from previous steps, return it
    return routes[0] # Return the single remaining route


# --- Sample Data for Testing ---
if __name__ == "__main__":
    # All routes are for the same destination prefix 8.8.8.0/24
    print("--- Sample Route Data ---")

    route1 = Route(
        prefix="8.8.8.0/24",
        as_path=[65002, 65001],
        next_hop="192.168.1.1",
        local_pref=100,
        origin='i',
        med=0,
        source='eBGP', # Learned from an external peer
        router_id="1.1.1.1" # Router ID of advertising peer
    )

    route2 = Route(
        prefix="8.8.8.0/24",
        as_path=[65003, 65001], # Same AS_PATH length as route1
        next_hop="192.168.1.2",
        local_pref=150, # Higher LOCAL_PREF
        origin='i',
        med=0,
        source='eBGP',
        router_id="2.2.2.2"
    )

    route3 = Route(
        prefix="8.8.8.0/24",
        as_path=[65004, 65005, 65001], # Longer AS_PATH
        next_hop="192.168.1.3",
        local_pref=100,
        origin='i',
        med=10, # Higher MED (less preferred)
        source='eBGP',
        router_id="3.3.3.3"
    )

    route4 = Route(
        prefix="8.8.8.0/24",
        as_path=[], # Locally originated
        next_hop="0.0.0.0", # Usually 0.0.0.0 for locally originated
        local_pref=200, # Highest LOCAL_PREF
        origin='i',
        med=0,
        source='iBGP', # Representing local origin
        router_id="0.0.0.0" # Router's own ID
    )

    all_routes = [route1, route2, route3, route4]

    for i, route in enumerate(all_routes):
        print(f"Route {i+1}: {route}")
    print("\n")

    best_route = select_best_path(all_routes)
    print(f"Best Path Selected: {best_route}")