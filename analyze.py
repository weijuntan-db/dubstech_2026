"""Deep analysis of the stop barrier data to find compelling insights."""
import json
from collections import defaultdict, Counter

with open("/home/weijun.tan/dubstech/webapp/data/stops.json") as f:
    stops = json.load(f)

# Filter to Seattle only (has neighborhood)
seattle_stops = [s for s in stops if s["neighborhood"]]
all_stops_count = len(seattle_stops)

print(f"=== BASIC STATS ===")
print(f"Total Seattle stops: {all_stops_count}")

# Severity >= 3, non-temporary (already filtered in preprocessing)
def get_barriers(stop, min_sev=3):
    return sum(v for k, v in stop["severity"].items() if int(k) >= min_sev)

impacted = [s for s in seattle_stops if get_barriers(s) > 0]
print(f"Stops with barriers (sev>=3): {len(impacted)} ({len(impacted)/all_stops_count*100:.1f}%)")

total_barriers = sum(get_barriers(s) for s in seattle_stops)
print(f"Total barriers: {total_barriers}")

# What % of stops account for what % of barriers?
print(f"\n=== CONCENTRATION ANALYSIS ===")
barrier_counts = sorted([get_barriers(s) for s in seattle_stops if get_barriers(s) > 0], reverse=True)
top_10pct = int(len(barrier_counts) * 0.1)
top_10pct_barriers = sum(barrier_counts[:top_10pct])
print(f"Top 10% of impacted stops ({top_10pct} stops) account for {top_10pct_barriers}/{total_barriers} barriers ({top_10pct_barriers/total_barriers*100:.1f}%)")

top_20pct = int(len(barrier_counts) * 0.2)
top_20pct_barriers = sum(barrier_counts[:top_20pct])
print(f"Top 20% of impacted stops ({top_20pct} stops) account for {top_20pct_barriers}/{total_barriers} barriers ({top_20pct_barriers/total_barriers*100:.1f}%)")

# What if we fixed the top N stops?
print(f"\n=== IMPACT OF FIXING TOP STOPS ===")
all_sorted = sorted(seattle_stops, key=lambda s: get_barriers(s), reverse=True)
for n in [50, 100, 200]:
    fixed = sum(get_barriers(s) for s in all_sorted[:n])
    print(f"Fixing top {n} stops would address {fixed}/{total_barriers} barriers ({fixed/total_barriers*100:.1f}%)")

# Barrier types analysis
print(f"\n=== BARRIER TYPES ===")
type_counts = Counter()
for s in seattle_stops:
    for t in s["barrier_types"]:
        type_counts[t] += 1
for t, c in type_counts.most_common():
    print(f"  {t}: {c} stops ({c/len(impacted)*100:.1f}% of impacted)")

# Neighborhood analysis
print(f"\n=== NEIGHBORHOODS (by total barriers) ===")
nbh = defaultdict(lambda: {"barriers": 0, "stops": 0, "total_stops": 0, "types": Counter()})
for s in seattle_stops:
    n = nbh[s["neighborhood"]]
    n["total_stops"] += 1
    bc = get_barriers(s)
    if bc > 0:
        n["barriers"] += bc
        n["stops"] += 1
        for t in s["barrier_types"]:
            n["types"][t] += 1

nbh_sorted = sorted(nbh.items(), key=lambda x: x[1]["barriers"], reverse=True)
print(f"Top 10 neighborhoods by total barriers:")
for name, n in nbh_sorted[:10]:
    pct = n["stops"]/n["total_stops"]*100 if n["total_stops"] > 0 else 0
    friction = n["barriers"]/n["stops"] if n["stops"] > 0 else 0
    top_type = n["types"].most_common(1)[0][0] if n["types"] else "N/A"
    print(f"  {name}: {n['barriers']} barriers, {n['stops']}/{n['total_stops']} stops impacted ({pct:.0f}%), friction={friction:.1f}, top_type={top_type}")

# Neighborhood with highest % impacted
print(f"\nNeighborhoods by % of stops impacted (min 10 stops):")
nbh_pct = [(name, n["stops"]/n["total_stops"]*100, n) for name, n in nbh.items() if n["total_stops"] >= 10]
nbh_pct.sort(key=lambda x: x[1], reverse=True)
for name, pct, n in nbh_pct[:10]:
    print(f"  {name}: {pct:.0f}% ({n['stops']}/{n['total_stops']} stops), {n['barriers']} barriers")

# Route analysis
print(f"\n=== ROUTES ===")
route_data = defaultdict(lambda: {"friction": 0, "stops": 0})
for s in seattle_stops:
    bc = get_barriers(s)
    if bc == 0:
        continue
    for r in s["routes"]:
        route_data[r]["friction"] += bc
        route_data[r]["stops"] += 1

routes_sorted = sorted(route_data.items(), key=lambda x: x[1]["friction"], reverse=True)
print(f"Top 10 routes by total friction:")
for route, r in routes_sorted[:10]:
    fps = r["friction"]/r["stops"] if r["stops"] > 0 else 0
    print(f"  Route {route}: {r['friction']} barriers across {r['stops']} stops (friction/stop={fps:.1f})")

# Routes by friction per stop (min 5 stops)
routes_fps = [(route, r["friction"]/r["stops"], r) for route, r in route_data.items() if r["stops"] >= 5]
routes_fps.sort(key=lambda x: x[1], reverse=True)
print(f"\nTop 10 routes by friction per stop (min 5 impacted stops):")
for route, fps, r in routes_fps[:10]:
    print(f"  Route {route}: {fps:.1f} barriers/stop ({r['friction']} barriers, {r['stops']} stops)")

# How many routes share the worst stops?
print(f"\n=== SHARED BURDEN ===")
worst_50 = all_sorted[:50]
routes_on_worst = Counter()
for s in worst_50:
    for r in s["routes"]:
        routes_on_worst[r] += 1
print(f"Routes passing through the 50 worst stops:")
for route, count in routes_on_worst.most_common(10):
    print(f"  Route {route}: passes through {count} of the 50 worst stops")

# Severity distribution
print(f"\n=== SEVERITY DISTRIBUTION ===")
sev_total = Counter()
for s in seattle_stops:
    for k, v in s["severity"].items():
        sev_total[int(k)] += v
total_all = sum(sev_total.values())
for sev in sorted(sev_total.keys()):
    print(f"  Severity {sev}: {sev_total[sev]} ({sev_total[sev]/total_all*100:.1f}%)")

# Stops with 0 barriers (in coverage area)
zero_barrier = [s for s in seattle_stops if get_barriers(s) == 0]
print(f"\n=== ZERO BARRIER STOPS ===")
print(f"Stops with zero barriers (sev>=3): {len(zero_barrier)} ({len(zero_barrier)/all_stops_count*100:.1f}%)")
