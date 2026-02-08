"""
Pre-compute the geo-proximity joins from raw CSVs and output JSON for the web app.
Matches the dashboard SQL logic: barriers within 0.0005 degrees of a transit stop.
"""
import csv
import json
from collections import defaultdict

DATA_DIR = "/home/weijun.tan/dubstech"
OUT_DIR = "/home/weijun.tan/dubstech/webapp/data"

GRID_SIZE = 0.001  # ~100m, covers the 0.0005 degree proximity threshold


def load_csv(path):
    with open(path, "r") as f:
        return list(csv.DictReader(f))


def grid_key(lon, lat):
    return (round(lon / GRID_SIZE), round(lat / GRID_SIZE))


def main():
    print("Loading CSVs...")
    barriers = load_csv(f"{DATA_DIR}/access_to_everyday_life_dataset.csv")
    stops = load_csv(f"{DATA_DIR}/transit_stop_latlon.csv")
    routes = load_csv(f"{DATA_DIR}/transit_stop_route_exploded_clean.csv")

    print(f"  Barriers: {len(barriers)}, Stops: {len(stops)}, Routes: {len(routes)}")

    # Build route lookup: stop_id -> [route_nums]
    route_map = defaultdict(set)
    for r in routes:
        route_map[r["STOP_ID"]].add(r["ROUTE_NUM"])

    # Build spatial index for barriers
    print("Building spatial index...")
    barrier_grid = defaultdict(list)
    for b in barriers:
        lon = float(b["geometry/coordinates/0"])
        lat = float(b["geometry/coordinates/1"])
        key = grid_key(lon, lat)
        barrier_grid[key].append(b)

    # Join: for each stop, find nearby barriers
    print("Computing stop-barrier joins...")
    stop_data = []
    for s in stops:
        lat = float(s["lat"])
        lon = float(s["lon"])
        stop_id = s["STOP_ID"]

        # Check neighboring grid cells
        center = grid_key(lon, lat)
        nearby_barriers = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                cell = (center[0] + dx, center[1] + dy)
                for b in barrier_grid.get(cell, []):
                    b_lon = float(b["geometry/coordinates/0"])
                    b_lat = float(b["geometry/coordinates/1"])
                    if abs(b_lon - lon) <= 0.0005 and abs(b_lat - lat) <= 0.0005:
                        nearby_barriers.append(b)

        # Count barriers by severity (only non-temporary)
        severity_counts = defaultdict(int)
        barrier_types = set()
        barrier_ids = set()
        neighborhoods = defaultdict(int)

        for b in nearby_barriers:
            if b["properties/is_temporary"] == "true":
                continue
            bid = b["properties/attribute_id"]
            if bid in barrier_ids:
                continue
            sev_str = b["properties/severity"]
            if not sev_str:
                continue
            barrier_ids.add(bid)
            sev = int(sev_str)
            severity_counts[sev] += 1
            barrier_types.add(b["properties/label_type"])
            nbh = b["properties/neighborhood"]
            if nbh:
                neighborhoods[nbh] += 1

        # Most common neighborhood for this stop
        neighborhood = max(neighborhoods, key=neighborhoods.get) if neighborhoods else None

        stop_entry = {
            "id": stop_id,
            "name": s["HASTUS_CROSS_STREET_NAME"],
            "lat": lat,
            "lon": lon,
            "routes": sorted(route_map.get(stop_id, [])),
            "neighborhood": neighborhood,
            "barrier_types": sorted(barrier_types),
            "severity": {str(k): v for k, v in sorted(severity_counts.items())},
            "total_barriers": len(barrier_ids),
        }
        stop_data.append(stop_entry)

    # Write stops JSON
    with open(f"{OUT_DIR}/stops.json", "w") as f:
        json.dump(stop_data, f)
    print(f"  Wrote {len(stop_data)} stops to stops.json")

    # Pre-aggregate neighborhoods (at default severity >= 3)
    print("Aggregating neighborhoods...")
    nbh_agg = defaultdict(lambda: {"lat_sum": 0, "lon_sum": 0, "count": 0, "barriers": 0, "stops": 0})
    for s in stop_data:
        if not s["neighborhood"]:
            continue
        severe = sum(v for k, v in s["severity"].items() if int(k) >= 3)
        if severe == 0:
            continue
        n = nbh_agg[s["neighborhood"]]
        n["lat_sum"] += s["lat"]
        n["lon_sum"] += s["lon"]
        n["count"] += 1
        n["barriers"] += severe
        n["stops"] += 1

    neighborhoods_out = []
    for name, n in nbh_agg.items():
        if n["count"] == 0:
            continue
        neighborhoods_out.append({
            "name": name,
            "lat": round(n["lat_sum"] / n["count"], 6),
            "lon": round(n["lon_sum"] / n["count"], 6),
            "impacted_stops": n["stops"],
            "total_barriers": n["barriers"],
            "friction_intensity": round(n["barriers"] / n["stops"], 1),
        })
    neighborhoods_out.sort(key=lambda x: x["friction_intensity"], reverse=True)

    with open(f"{OUT_DIR}/neighborhoods.json", "w") as f:
        json.dump(neighborhoods_out, f)
    print(f"  Wrote {len(neighborhoods_out)} neighborhoods to neighborhoods.json")

    # Pre-aggregate routes (at default severity >= 3)
    print("Aggregating routes...")
    route_agg = defaultdict(lambda: {"total_friction": 0, "impacted_stops": 0})
    for s in stop_data:
        severe = sum(v for k, v in s["severity"].items() if int(k) >= 3)
        if severe == 0:
            continue
        for route in s["routes"]:
            r = route_agg[route]
            r["total_friction"] += severe
            r["impacted_stops"] += 1

    routes_out = []
    for route_num, r in route_agg.items():
        routes_out.append({
            "route": route_num,
            "total_friction": r["total_friction"],
            "impacted_stops": r["impacted_stops"],
            "friction_per_stop": round(r["total_friction"] / r["impacted_stops"], 2) if r["impacted_stops"] else 0,
        })
    routes_out.sort(key=lambda x: x["total_friction"], reverse=True)

    with open(f"{OUT_DIR}/routes.json", "w") as f:
        json.dump(routes_out, f)
    print(f"  Wrote {len(routes_out)} routes to routes.json")

    print("Done!")


if __name__ == "__main__":
    main()
