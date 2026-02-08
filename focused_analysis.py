"""
Focused analysis: build a cohesive 3-part argument with deep supporting evidence.
"""
import json
from collections import defaultdict, Counter

with open("/home/weijun.tan/dubstech/webapp/data/stops.json") as f:
    stops = json.load(f)

seattle = [s for s in stops if s["neighborhood"]]

def get_barriers(stop, min_sev=3):
    return sum(v for k, v in stop["severity"].items() if int(k) >= min_sev)

impacted = [s for s in seattle if get_barriers(s) > 0]
total_barriers = sum(get_barriers(s) for s in seattle)

print("=" * 70)
print("ARGUMENT 1: The problem is extremely concentrated")
print("  (Therefore: targeted fixes work)")
print("=" * 70)

# Pareto at multiple thresholds
sorted_stops = sorted(impacted, key=lambda s: get_barriers(s), reverse=True)
for n in [50, 100, 150, 200, 271, 500]:
    fixed = sum(get_barriers(s) for s in sorted_stops[:n])
    pct_stops = n / len(impacted) * 100
    pct_barriers = fixed / total_barriers * 100
    print(f"  Top {n} stops ({pct_stops:.1f}% of impacted) = {fixed} barriers ({pct_barriers:.1f}% of total)")

# How many neighborhoods contain the top 271 stops?
top271 = sorted_stops[:271]
top271_nbhs = Counter(s["neighborhood"] for s in top271)
print(f"\n  The 271 worst stops span only {len(top271_nbhs)} neighborhoods:")
for nbh, count in top271_nbhs.most_common():
    print(f"    {nbh}: {count} stops")

# What's the overlap in routes? If we fix the worst stops, how many routes benefit?
routes_benefiting = set()
for s in top271:
    for r in s["routes"]:
        routes_benefiting.add(r)
print(f"\n  Fixing these 271 stops improves {len(routes_benefiting)} bus routes")

# Average barrier types per stop in top 271 vs. all impacted
top_avg_types = sum(len(s["barrier_types"]) for s in top271) / len(top271)
all_avg_types = sum(len(s["barrier_types"]) for s in impacted) / len(impacted)
print(f"\n  Avg barrier types at top-271 stops: {top_avg_types:.1f} (vs {all_avg_types:.1f} overall)")
print(f"  → Worst stops have MORE types compounding = higher bang-for-buck per fix")

# Co-occurrence at top stops
print(f"\n  Barrier type co-occurrence at the 271 worst stops:")
type_counts_top = Counter()
for s in top271:
    for t in s["barrier_types"]:
        type_counts_top[t] += 1
for t, c in type_counts_top.most_common():
    print(f"    {t}: present at {c}/{len(top271)} stops ({c/len(top271)*100:.0f}%)")


print("\n" + "=" * 70)
print("ARGUMENT 2: Different barrier types need different fixes")
print("  (Therefore: separate maintenance vs capital budgets)")
print("=" * 70)

import csv
with open("/home/weijun.tan/dubstech/access_to_everyday_life_dataset.csv") as f:
    raw = list(csv.DictReader(f))

# Severity profile per type (sev >= 3 only)
type_data = defaultdict(lambda: {"count": 0, "sev_sum": 0, "sev5": 0, "stops": set()})
for b in raw:
    if b["properties/is_temporary"] == "true":
        continue
    sev_str = b["properties/severity"]
    if not sev_str or int(sev_str) < 3:
        continue
    btype = b["properties/label_type"]
    sev = int(sev_str)
    type_data[btype]["count"] += 1
    type_data[btype]["sev_sum"] += sev
    if sev == 5:
        type_data[btype]["sev5"] += 1

total_sev3 = sum(d["count"] for d in type_data.values())

print("\n  Barrier types ranked by volume (severity >= 3):")
for btype in sorted(type_data, key=lambda t: -type_data[t]["count"]):
    d = type_data[btype]
    avg = d["sev_sum"] / d["count"]
    pct = d["count"] / total_sev3 * 100
    s5pct = d["sev5"] / d["count"] * 100
    print(f"    {btype}: {d['count']} ({pct:.0f}%), avg severity {avg:.1f}, {s5pct:.0f}% are sev-5")

# The key insight: CurbRamp dominates by STOP count but is low severity
# NoSidewalk + NoCurbRamp dominate by BARRIER count and are high severity
print("\n  Two distinct fix categories emerge:")
maintenance = type_data["CurbRamp"]["count"] + type_data["SurfaceProblem"]["count"]
capital = type_data["NoSidewalk"]["count"] + type_data["NoCurbRamp"]["count"]
print(f"    MAINTENANCE (CurbRamp + SurfaceProblem): {maintenance} barriers ({maintenance/total_sev3*100:.0f}%)")
print(f"      → Existing infrastructure that's degraded. Needs repair crews.")
maint_avg = (type_data["CurbRamp"]["sev_sum"] + type_data["SurfaceProblem"]["sev_sum"]) / maintenance
print(f"      → Average severity: {maint_avg:.1f}")
print(f"    CAPITAL (NoSidewalk + NoCurbRamp): {capital} barriers ({capital/total_sev3*100:.0f}%)")
print(f"      → Infrastructure that was never built. Needs new construction.")
cap_avg = (type_data["NoSidewalk"]["sev_sum"] + type_data["NoCurbRamp"]["sev_sum"]) / capital
print(f"      → Average severity: {cap_avg:.1f}")


print("\n" + "=" * 70)
print("ARGUMENT 3: Equity — the worst barriers hit the most vulnerable")
print("  (Therefore: prioritize by need, not just by count)")
print("=" * 70)

# Trapped stops analysis (high barriers, few routes)
trapped = [(s, get_barriers(s)) for s in impacted if get_barriers(s) >= 5 and len(s["routes"]) <= 1]
trapped.sort(key=lambda x: -x[1])

# Where are trapped stops?
trapped_nbh = Counter(s["neighborhood"] for s, _ in trapped)
print(f"\n  {len(trapped)} 'trapped' stops (5+ barriers, 0-1 routes)")
print(f"  Top neighborhoods with trapped stops:")
for nbh, count in trapped_nbh.most_common(5):
    # What % of that neighborhood's impacted stops are trapped?
    nbh_impacted = len([s for s in impacted if s["neighborhood"] == nbh])
    print(f"    {nbh}: {count} trapped / {nbh_impacted} impacted ({count/nbh_impacted*100:.0f}%)")

# Yesler Terrace deep dive
yt = [s for s in seattle if s["neighborhood"] == "Yesler Terrace"]
yt_impacted = [s for s in yt if get_barriers(s) > 0]
yt_barriers = sum(get_barriers(s) for s in yt)
yt_trapped = [s for s in yt if get_barriers(s) >= 5 and len(s["routes"]) <= 1]
yt_routes = set()
for s in yt:
    for r in s["routes"]:
        yt_routes.add(r)
print(f"\n  Yesler Terrace (public housing):")
print(f"    {len(yt_impacted)}/{len(yt)} stops impacted ({len(yt_impacted)/len(yt)*100:.0f}%)")
print(f"    {yt_barriers} total barriers")
print(f"    {len(yt_trapped)} trapped stops")
print(f"    Served by {len(yt_routes)} routes: {sorted(yt_routes)}")

# Compare: stops with 0 routes vs 3+ routes
zero_route = [s for s in impacted if len(s["routes"]) == 0]
multi_route = [s for s in impacted if len(s["routes"]) >= 3]
zero_avg = sum(get_barriers(s) for s in zero_route) / len(zero_route) if zero_route else 0
multi_avg = sum(get_barriers(s) for s in multi_route) / len(multi_route) if multi_route else 0
print(f"\n  Route access vs barrier burden:")
print(f"    Stops with 0 routes: avg {zero_avg:.1f} barriers ({len(zero_route)} stops)")
print(f"    Stops with 3+ routes: avg {multi_avg:.1f} barriers ({len(multi_route)} stops)")
print(f"    → {zero_avg/multi_avg:.1f}x more barriers at stops with no route alternatives")

# Industrial District: most trapped stops but NOT public housing
ind = [s for s in impacted if s["neighborhood"] == "Industrial District"]
ind_trapped = [s for s in ind if get_barriers(s) >= 5 and len(s["routes"]) <= 1]
print(f"\n  Industrial District:")
print(f"    {len(ind)} impacted stops, {len(ind_trapped)} trapped")
print(f"    {sum(get_barriers(s) for s in ind)} total barriers (most of any neighborhood)")

print("\n" + "=" * 70)
print("SUMMARY: The cohesive argument")
print("=" * 70)
print("""
  1. CONCENTRATED: 8% of stops hold 25% of barriers. The worst 271 stops
     cluster in just a handful of neighborhoods, compound multiple barrier
     types, and touch dozens of routes. Targeted investment works.

  2. TWO FIX TRACKS: 72% of severe barriers split into two categories —
     maintenance (repair degraded ramps/surfaces) vs capital (build missing
     sidewalks/ramps). These need separate budgets and timelines.
     Capital projects address the higher-severity barriers.

  3. EQUITY GAP: Stops with fewer routes have more barriers — the inverse
     of what equitable transit requires. 960 trapped stops have barriers
     AND no alternatives. Yesler Terrace (public housing) is 100% impacted.
     Prioritize by vulnerability, not just volume.
""")
