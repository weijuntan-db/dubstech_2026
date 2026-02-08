"""
Deep analysis of Seattle transit accessibility barriers.
Goes beyond the basic analyze.py to find hidden, surprising, and actionable insights.
"""
import json
import csv
from collections import defaultdict, Counter
from itertools import combinations

DATA_DIR = "/home/weijun.tan/dubstech"

# Load processed stops
with open(f"{DATA_DIR}/webapp/data/stops.json") as f:
    stops = json.load(f)

# Load raw barriers for per-barrier analysis
with open(f"{DATA_DIR}/access_to_everyday_life_dataset.csv") as f:
    raw_barriers = list(csv.DictReader(f))

# Load route mappings
with open(f"{DATA_DIR}/transit_stop_route_exploded_clean.csv") as f:
    route_rows = list(csv.DictReader(f))

route_map = defaultdict(set)
for r in route_rows:
    route_map[r["STOP_ID"]].add(r["ROUTE_NUM"])

seattle = [s for s in stops if s["neighborhood"]]


def get_barriers(stop, min_sev=3):
    return sum(v for k, v in stop["severity"].items() if int(k) >= min_sev)


impacted = [s for s in seattle if get_barriers(s) > 0]
total_barriers = sum(get_barriers(s) for s in seattle)

print("=" * 70)
print("DEEP ANALYSIS: Seattle Transit Accessibility Barriers")
print("=" * 70)

# ──────────────────────────────────────────────────────────────────────
# 1. CO-OCCURRENCE ANALYSIS: Which barrier types cluster together?
# ──────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("1. BARRIER TYPE CO-OCCURRENCE")
print("   Which types appear together at the same stops?")
print("=" * 70)

pair_counts = Counter()
single_counts = Counter()
for s in impacted:
    types = s["barrier_types"]
    for t in types:
        single_counts[t] += 1
    for pair in combinations(sorted(types), 2):
        pair_counts[pair] += 1

print("\nMost common type pairs at impacted stops:")
for (a, b), count in pair_counts.most_common(10):
    # Calculate: what % of stops with type A also have type B?
    pct_a = count / single_counts[a] * 100 if single_counts[a] else 0
    pct_b = count / single_counts[b] * 100 if single_counts[b] else 0
    print(f"  {a} + {b}: {count} stops")
    print(f"    {pct_a:.0f}% of {a} stops also have {b}")
    print(f"    {pct_b:.0f}% of {b} stops also have {a}")

# Exclusive types (stops that ONLY have one type)
print("\nStops with ONLY one barrier type:")
for s in impacted:
    if len(s["barrier_types"]) == 1:
        single_counts_exclusive = Counter()
for s in impacted:
    if len(s["barrier_types"]) == 1:
        single_counts_exclusive[s["barrier_types"][0]] = single_counts_exclusive.get(s["barrier_types"][0], 0) + 1

exclusive_counts = defaultdict(int)
for s in impacted:
    if len(s["barrier_types"]) == 1:
        exclusive_counts[s["barrier_types"][0]] += 1

for t, count in sorted(exclusive_counts.items(), key=lambda x: -x[1]):
    pct = count / single_counts[t] * 100
    print(f"  {t}: {count} stops are {t}-only ({pct:.0f}% of all {t} stops)")

# ──────────────────────────────────────────────────────────────────────
# 2. SEVERITY VS TYPE: Are certain barrier types more severe?
# ──────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("2. SEVERITY BY BARRIER TYPE (from raw data)")
print("   Are some barrier types consistently more severe?")
print("=" * 70)

type_severity = defaultdict(lambda: defaultdict(int))
for b in raw_barriers:
    if b["properties/is_temporary"] == "true":
        continue
    sev = b["properties/severity"]
    if not sev:
        continue
    btype = b["properties/label_type"]
    type_severity[btype][int(sev)] += 1

for btype in sorted(type_severity.keys()):
    sevs = type_severity[btype]
    total = sum(sevs.values())
    avg_sev = sum(s * c for s, c in sevs.items()) / total if total else 0
    high_sev_pct = sum(c for s, c in sevs.items() if s >= 4) / total * 100 if total else 0
    dist = " | ".join(f"sev{s}:{c}" for s, c in sorted(sevs.items()))
    print(f"\n  {btype} (n={total}, avg_severity={avg_sev:.2f}, {high_sev_pct:.0f}% are sev 4-5)")
    print(f"    {dist}")

# ──────────────────────────────────────────────────────────────────────
# 3. GEOGRAPHIC CLUSTERS: Nearby neighborhoods with similar profiles
# ──────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("3. NEIGHBORHOOD BARRIER PROFILES")
print("   What's the dominant barrier type per neighborhood?")
print("=" * 70)

nbh_types = defaultdict(lambda: Counter())
nbh_sev = defaultdict(lambda: defaultdict(int))
nbh_stop_count = defaultdict(int)
nbh_total_barriers = defaultdict(int)

for s in impacted:
    n = s["neighborhood"]
    nbh_stop_count[n] += 1
    bc = get_barriers(s)
    nbh_total_barriers[n] += bc
    for t in s["barrier_types"]:
        nbh_types[n][t] += 1
    for sev_str, count in s["severity"].items():
        if int(sev_str) >= 3:
            nbh_sev[n][int(sev_str)] += count

print("\nNeighborhood profiles (dominant type, avg severity):")
profiles = []
for n in sorted(nbh_types.keys()):
    types = nbh_types[n]
    total_type_mentions = sum(types.values())
    dominant = types.most_common(1)[0]
    dom_pct = dominant[1] / total_type_mentions * 100
    sevs = nbh_sev[n]
    total_sev = sum(sevs.values())
    avg_sev = sum(s * c for s, c in sevs.items()) / total_sev if total_sev else 0
    high_sev_pct = sum(c for s, c in sevs.items() if s >= 4) / total_sev * 100 if total_sev else 0
    profiles.append((n, dominant[0], dom_pct, avg_sev, high_sev_pct, nbh_stop_count[n], nbh_total_barriers[n]))

# Sort by avg severity
profiles.sort(key=lambda x: -x[3])
print("\nTop 15 neighborhoods by average barrier severity:")
for n, dom, dom_pct, avg_sev, high_pct, stops, barriers in profiles[:15]:
    print(f"  {n}: avg_sev={avg_sev:.2f}, {high_pct:.0f}% sev4-5, dominant={dom} ({dom_pct:.0f}%), {stops} stops, {barriers} barriers")

# Find neighborhoods where dominant type is NOT CurbRamp (unusual)
print("\nNeighborhoods where CurbRamp is NOT the dominant type (min 20 stops):")
for n, dom, dom_pct, avg_sev, high_pct, stop_ct, barriers in profiles:
    if dom != "CurbRamp" and stop_ct >= 20:
        types_str = ", ".join(f"{t}:{c}" for t, c in nbh_types[n].most_common(3))
        print(f"  {n}: dominant={dom} ({dom_pct:.0f}%), types=[{types_str}], {stop_ct} stops")

# ──────────────────────────────────────────────────────────────────────
# 4. ROUTE CORRIDOR ANALYSIS: Routes that share the worst stops
# ──────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("4. ROUTE OVERLAP ON WORST STOPS")
print("   Which routes share the most high-barrier stops?")
print("=" * 70)

# Get stops with 10+ barriers
worst_stops = [s for s in seattle if get_barriers(s) >= 10]
print(f"\nStops with 10+ barriers: {len(worst_stops)}")

route_overlap = Counter()
for s in worst_stops:
    routes = s["routes"]
    for pair in combinations(sorted(routes), 2):
        route_overlap[pair] += 1

print("\nRoute pairs sharing the most 10+ barrier stops:")
for (r1, r2), count in route_overlap.most_common(15):
    print(f"  Routes {r1} & {r2}: share {count} high-barrier stops")

# ──────────────────────────────────────────────────────────────────────
# 5. "BARRIER DESERTS" - Routes with surprisingly few barriers
# ──────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("5. BARRIER DESERTS: Routes with surprisingly low friction")
print("   Which major routes are the most accessible?")
print("=" * 70)

route_stats = defaultdict(lambda: {"friction": 0, "stops": 0, "total_stops": 0})
for s in seattle:
    bc = get_barriers(s)
    for r in s["routes"]:
        route_stats[r]["total_stops"] += 1
        if bc > 0:
            route_stats[r]["stops"] += 1
            route_stats[r]["friction"] += bc

# Major routes only (20+ total stops)
major_routes = [(r, d) for r, d in route_stats.items() if d["total_stops"] >= 20]
major_routes.sort(key=lambda x: x[1]["friction"] / max(x[1]["total_stops"], 1))

print("\nMost accessible major routes (20+ stops, lowest friction/total_stops):")
for r, d in major_routes[:10]:
    fps = d["friction"] / d["total_stops"] if d["total_stops"] else 0
    impact_pct = d["stops"] / d["total_stops"] * 100 if d["total_stops"] else 0
    print(f"  Route {r}: {fps:.1f} barriers/total_stop, {impact_pct:.0f}% stops impacted, {d['total_stops']} total stops")

# ──────────────────────────────────────────────────────────────────────
# 6. STOP ISOLATION: High-barrier stops with few route options
# ──────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("6. TRAPPED STOPS: High barriers + few route alternatives")
print("   Where are people most trapped by barriers?")
print("=" * 70)

trapped = []
for s in impacted:
    bc = get_barriers(s)
    route_count = len(s["routes"])
    if bc >= 5 and route_count <= 1:
        trapped.append((s, bc, route_count))

trapped.sort(key=lambda x: -x[1])
print(f"\nStops with 5+ barriers and only 0-1 routes: {len(trapped)}")
print("\nWorst 15 'trapped' stops:")
for s, bc, rc in trapped[:15]:
    routes = ", ".join(s["routes"]) if s["routes"] else "NO ROUTES"
    print(f"  {s['name']} (ID:{s['id']}): {bc} barriers, routes=[{routes}], {s['neighborhood']}")

# By neighborhood
trapped_by_nbh = Counter()
for s, bc, rc in trapped:
    trapped_by_nbh[s["neighborhood"]] += 1

print("\nNeighborhoods with most 'trapped' stops:")
for n, count in trapped_by_nbh.most_common(10):
    print(f"  {n}: {count} trapped stops")

# ──────────────────────────────────────────────────────────────────────
# 7. MULTI-TYPE BURDEN: Stops hit by 4+ different barrier types
# ──────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("7. MULTI-TYPE BURDEN: Stops with 4+ barrier types")
print("   Where are ALL kinds of problems converging?")
print("=" * 70)

multi_type = [(s, len(s["barrier_types"]), get_barriers(s))
              for s in impacted if len(s["barrier_types"]) >= 4]
multi_type.sort(key=lambda x: -x[1])

print(f"\nStops with 4+ barrier types: {len(multi_type)}")
for s, tc, bc in multi_type[:15]:
    print(f"  {s['name']} ({s['neighborhood']}): {tc} types [{', '.join(s['barrier_types'])}], {bc} barriers, routes=[{', '.join(s['routes'][:3])}]")

# ──────────────────────────────────────────────────────────────────────
# 8. SEVERITY ESCALATION: Neighborhoods where barriers are getting worse
#    (High proportion of severity 5)
# ──────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("8. SEVERITY HOTSPOTS")
print("   Neighborhoods with highest proportion of severity 5 barriers")
print("=" * 70)

nbh_sev5 = []
for n in nbh_sev:
    sevs = nbh_sev[n]
    total = sum(sevs.values())
    sev5 = sevs.get(5, 0)
    if total >= 50:  # minimum sample size
        nbh_sev5.append((n, sev5, total, sev5 / total * 100))

nbh_sev5.sort(key=lambda x: -x[3])
print(f"\nNeighborhoods with highest % of severity-5 barriers (min 50 barriers):")
for n, s5, total, pct in nbh_sev5[:15]:
    print(f"  {n}: {pct:.0f}% sev-5 ({s5}/{total} barriers)")

# ──────────────────────────────────────────────────────────────────────
# 9. BANG-FOR-BUCK: If you could fix ONE barrier type everywhere
# ──────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("9. BANG FOR BUCK: Impact of fixing one barrier type city-wide")
print("=" * 70)

# From raw data, count barriers by type (severity >= 3)
type_barrier_count = Counter()
type_barrier_sev = defaultdict(int)
for b in raw_barriers:
    if b["properties/is_temporary"] == "true":
        continue
    sev = b["properties/severity"]
    if not sev or int(sev) < 3:
        continue
    btype = b["properties/label_type"]
    type_barrier_count[btype] += 1
    type_barrier_sev[btype] += int(sev)

total_raw = sum(type_barrier_count.values())
print(f"\nTotal barriers (sev >= 3): {total_raw}")
for btype, count in type_barrier_count.most_common():
    pct = count / total_raw * 100
    avg_sev = type_barrier_sev[btype] / count if count else 0
    print(f"  Fix all {btype}: eliminates {count} barriers ({pct:.0f}% of total), avg severity {avg_sev:.1f}")

# ──────────────────────────────────────────────────────────────────────
# 10. SURPRISING FILTER COMBOS TO EXPLORE
# ──────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("10. SUGGESTED FILTER COMBOS FOR USERS TO EXPLORE")
print("=" * 70)

suggestions = []

# Find the route with worst NoCurbRamp concentration
route_nocurb = defaultdict(int)
route_total = defaultdict(int)
for s in impacted:
    if "NoCurbRamp" in s["barrier_types"]:
        for r in s["routes"]:
            route_nocurb[r] += 1
    for r in s["routes"]:
        route_total[r] += 1

worst_nocurb_routes = []
for r in route_nocurb:
    if route_total[r] >= 15:
        pct = route_nocurb[r] / route_total[r] * 100
        worst_nocurb_routes.append((r, pct, route_nocurb[r], route_total[r]))
worst_nocurb_routes.sort(key=lambda x: -x[1])

# Find the route with worst NoSidewalk
route_nosidewalk = defaultdict(int)
for s in impacted:
    if "NoSidewalk" in s["barrier_types"]:
        for r in s["routes"]:
            route_nosidewalk[r] += 1

worst_nosidewalk_routes = []
for r in route_nosidewalk:
    if route_total[r] >= 10:
        pct = route_nosidewalk[r] / route_total[r] * 100
        worst_nosidewalk_routes.append((r, pct, route_nosidewalk[r]))
worst_nosidewalk_routes.sort(key=lambda x: -x[1])

# Find neighborhood with most Obstacle barriers
nbh_obstacle = defaultdict(int)
for s in impacted:
    if "Obstacle" in s["barrier_types"]:
        nbh_obstacle[s["neighborhood"]] += 1

print("""
These are interesting filter combinations that reveal hidden patterns.
Users should try these in the dashboard:

COMBO 1: "The Missing Ramps Corridor"
  Filter: Barrier Type = NoCurbRamp, Min Severity = 4
  Why: Shows where wheelchair users literally cannot reach bus stops.
  Watch for: Clusters along specific corridors, not random scatter.""")

if worst_nocurb_routes:
    r, pct, cnt, tot = worst_nocurb_routes[0]
    print(f"  Then try Route {r}: {pct:.0f}% of its impacted stops lack curb ramps ({cnt}/{tot} stops)")

print("""
COMBO 2: "The Invisible Sidewalks"
  Filter: Barrier Type = NoSidewalk, Min Barriers = 1, Min Severity = 3
  Why: These stops have NO sidewalk path at all — the most extreme barrier.
  Watch for: These tend to cluster in industrial/peripheral areas.""")

if worst_nosidewalk_routes:
    r, pct, cnt = worst_nosidewalk_routes[0]
    print(f"  Worst route: Route {r} ({pct:.0f}% of stops have no sidewalk, {cnt} stops)")

print("""
COMBO 3: "Severity 5 Only"
  Filter: Min Severity = 5, Min Barriers = 1
  Why: Strips away everything but the most critical barriers. The map
  goes sparse — these are the true emergency fixes.
  Watch for: Which neighborhoods STILL light up? Those need help first.""")

# Count sev-5 stops
sev5_stops = [s for s in seattle if sum(v for k, v in s["severity"].items() if int(k) == 5) > 0]
sev5_nbh = Counter(s["neighborhood"] for s in sev5_stops)
top3_sev5 = sev5_nbh.most_common(3)
print(f"  {len(sev5_stops)} stops have severity-5 barriers")
print(f"  Top neighborhoods: {', '.join(f'{n} ({c})' for n, c in top3_sev5)}")

print("""
COMBO 4: "The Single-Route Trap"
  Filter: Min Barriers = 8, then look for stops with only 1 route
  Why: People at these stops have NO alternative — one inaccessible stop
  means they have zero transit access.
  Watch for: Outer neighborhoods where bus coverage is thin.""")

single_route_bad = [(s, get_barriers(s)) for s in impacted
                    if get_barriers(s) >= 8 and len(s["routes"]) == 1]
single_route_bad.sort(key=lambda x: -x[1])
print(f"  {len(single_route_bad)} stops with 8+ barriers and only 1 route")
if single_route_bad:
    s, bc = single_route_bad[0]
    print(f"  Worst: {s['name']} ({s['neighborhood']}), {bc} barriers, only route {s['routes'][0]}")

print("""
COMBO 5: "CurbRamp vs NoCurbRamp — The Irony"
  Toggle between Barrier Type = CurbRamp then NoCurbRamp
  Why: CurbRamp means a ramp EXISTS but is damaged/blocked. NoCurbRamp
  means no ramp at all. Compare where each clusters — different problems
  need different fixes (repair vs. new construction).
  Watch for: NoCurbRamp clusters in older neighborhoods; CurbRamp issues
  appear even in newer areas (maintenance failure vs. design gap).""")

curb_nbhs = Counter()
nocurb_nbhs = Counter()
for s in impacted:
    if "CurbRamp" in s["barrier_types"]:
        curb_nbhs[s["neighborhood"]] += 1
    if "NoCurbRamp" in s["barrier_types"]:
        nocurb_nbhs[s["neighborhood"]] += 1

# Find neighborhoods where NoCurbRamp dominates over CurbRamp
print("\n  Neighborhoods where NoCurbRamp dominates (more NoCurbRamp than CurbRamp issues):")
for n in sorted(nocurb_nbhs.keys()):
    if nocurb_nbhs[n] > curb_nbhs.get(n, 0) and nocurb_nbhs[n] >= 10:
        ratio = nocurb_nbhs[n] / max(curb_nbhs.get(n, 1), 1)
        print(f"    {n}: {nocurb_nbhs[n]} NoCurbRamp vs {curb_nbhs.get(n, 0)} CurbRamp (ratio {ratio:.1f}x)")

print("""
COMBO 6: "Route 348 Deep Dive"
  Filter: Route = 348, Min Barriers = 0
  Why: The worst friction-per-stop of any major route (7.8 barriers/stop).
  Every stop on this route is severely impacted. Explore what types
  dominate and which neighborhoods it passes through.""")

r348_stops = [s for s in seattle if "348" in s["routes"] and get_barriers(s) > 0]
r348_types = Counter()
r348_nbhs = Counter()
for s in r348_stops:
    for t in s["barrier_types"]:
        r348_types[t] += 1
    r348_nbhs[s["neighborhood"]] += 1
print(f"  Route 348: {len(r348_stops)} impacted stops")
print(f"  Barrier types: {', '.join(f'{t}:{c}' for t, c in r348_types.most_common())}")
print(f"  Neighborhoods: {', '.join(f'{n}({c})' for n, c in r348_nbhs.most_common())}")

print("""
COMBO 7: "The Equity Check"
  Filter: Route = any route through Yesler Terrace, Min Severity = 3
  Why: Yesler Terrace is public housing with 100% barrier impact.
  See which routes serve this community and how they compare to
  citywide averages.""")

yt_stops = [s for s in impacted if s["neighborhood"] == "Yesler Terrace"]
yt_routes = Counter()
for s in yt_stops:
    for r in s["routes"]:
        yt_routes[r] += 1
print(f"  Yesler Terrace: {len(yt_stops)} impacted stops")
print(f"  Routes serving YT: {', '.join(f'Route {r}({c} stops)' for r, c in yt_routes.most_common())}")

# ──────────────────────────────────────────────────────────────────────
# 11. HIDDEN PATTERN: Barrier density vs route count
# ──────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("11. DO MORE ROUTES = MORE BARRIERS? (correlation)")
print("=" * 70)

# Bucket stops by route count
route_bucket = defaultdict(lambda: {"stops": 0, "total_barriers": 0, "impacted": 0})
for s in seattle:
    rc = len(s["routes"])
    bucket = f"{rc}" if rc <= 4 else "5+"
    route_bucket[bucket]["stops"] += 1
    bc = get_barriers(s)
    route_bucket[bucket]["total_barriers"] += bc
    if bc > 0:
        route_bucket[bucket]["impacted"] += 1

print("\nBarrier density by # of routes serving a stop:")
for bucket in ["0", "1", "2", "3", "4", "5+"]:
    d = route_bucket.get(bucket)
    if d and d["stops"] > 0:
        avg = d["total_barriers"] / d["stops"]
        impact_pct = d["impacted"] / d["stops"] * 100
        print(f"  {bucket} routes: {d['stops']} stops, avg {avg:.1f} barriers, {impact_pct:.0f}% impacted")

# ──────────────────────────────────────────────────────────────────────
# 12. PARETO AT DIFFERENT SEVERITY LEVELS
# ──────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("12. CONCENTRATION: How many stops to fix X% of barriers?")
print("=" * 70)

for min_sev in [3, 4, 5]:
    barriers_at_sev = [(s, get_barriers(s, min_sev)) for s in seattle]
    barriers_at_sev = [(s, b) for s, b in barriers_at_sev if b > 0]
    barriers_at_sev.sort(key=lambda x: -x[1])
    total = sum(b for _, b in barriers_at_sev)
    if total == 0:
        continue

    for target_pct in [25, 50]:
        target = total * target_pct / 100
        running = 0
        for i, (s, b) in enumerate(barriers_at_sev):
            running += b
            if running >= target:
                print(f"  Severity >= {min_sev}: Fix {i+1} stops ({i+1}/{len(barriers_at_sev)} = {(i+1)/len(barriers_at_sev)*100:.0f}%) to eliminate {target_pct}% of barriers")
                break

print("\n" + "=" * 70)
print("ANALYSIS COMPLETE")
print("=" * 70)
