import osmnx as ox
import networkx as nx
import matplotlib.pyplot as plt

# ---------------------------------
# STEP 1: LOAD ROAD NETWORK
# ---------------------------------
CITY = "Bengaluru, India"
print("\nLoading road network...")
graph = ox.graph_from_place(CITY, network_type="drive")
print("Network loaded successfully")

# ---------------------------------
# STEP 2: ASSIGN SIGNAL TYPE
# ---------------------------------
for node in graph.nodes:
    if graph.degree[node] >= 4:
        graph.nodes[node]["signal"] = "automatic"
    else:
        graph.nodes[node]["signal"] = "manual"

# ---------------------------------
# STEP 3: VEHICLE SELECTION
# ---------------------------------
print("\nSelect vehicle type:")
print("1. Two Wheeler (Bike)")
print("2. Three Wheeler (Auto)")
print("3. Four Wheeler (Car)")

choice = input("Enter choice (1/2/3): ")
vehicle_map = {"1": "bike", "2": "auto", "3": "car"}
vehicle = vehicle_map.get(choice, "bike")

VEHICLE_SPEED = {
    "bike": 13.89,
    "auto": 11.11,
    "car": 16.67
}

ROAD_ACCESS = {
    "bike": ["primary", "secondary", "tertiary", "residential"],
    "auto": ["primary", "secondary", "tertiary", "residential", "trunk"],
    "car": ["motorway", "trunk", "primary", "secondary", "tertiary"]
}

speed = VEHICLE_SPEED[vehicle]
allowed_roads = ROAD_ACCESS[vehicle]

print(f"\nVehicle Selected: {vehicle.upper()}")

# ---------------------------------
# STEP 4: FILTER GRAPH BY VEHICLE
# ---------------------------------
filtered_graph = nx.MultiDiGraph()
filtered_graph.graph.update(graph.graph)

for u, v, data in graph.edges(data=True):
    road = data.get("highway", "residential")
    if isinstance(road, list):
        road = road[0]
    if road in allowed_roads:
        filtered_graph.add_edge(u, v, **data)

for n in filtered_graph.nodes:
    filtered_graph.nodes[n].update(graph.nodes[n])

# ---------------------------------
# STEP 5: SOURCE & DESTINATION
# ---------------------------------
src = input("\nEnter source location: ")
dst = input("Enter destination location: ")

src_point = ox.geocode(f"{src}, Bengaluru, India")
dst_point = ox.geocode(f"{dst}, Bengaluru, India")

source = ox.nearest_nodes(filtered_graph, src_point[1], src_point[0])
target = ox.nearest_nodes(filtered_graph, dst_point[1], dst_point[0])

# ---------------------------------
# STEP 6: COST FUNCTIONS
# ---------------------------------
def intelligent_cost(u, v, data):
    length = data.get("length", 1)

    if filtered_graph.nodes[v]["signal"] == "manual":
        signal_penalty = 30
    else:
        signal_penalty = 5

    alpha = 0.2  # balanced influence
    return (length / speed) + alpha * signal_penalty

# ---------------------------------
# STEP 7: ROUTE CALCULATION
# ---------------------------------
normal_route = nx.shortest_path(
    filtered_graph, source, target, weight="length"
)

intelligent_route = nx.shortest_path(
    filtered_graph, source, target, weight=intelligent_cost
)

# ---------------------------------
# STEP 8: ETA CALCULATION
# ---------------------------------
def calculate_eta(route, graph, speed, consider_signals=True):
    total_dist = 0
    total_time = 0

    for i in range(len(route) - 1):
        u, v = route[i], route[i + 1]
        edge = graph.get_edge_data(u, v)[0]
        length = edge.get("length", 0)
        total_dist += length

        if consider_signals:
            if graph.nodes[v]["signal"] == "manual":
                penalty = 30
            else:
                penalty = 5
            total_time += (length / speed) + 0.2 * penalty
        else:
            total_time += length / speed

    return total_dist / 1000, total_time / 60

normal_km, normal_eta = calculate_eta(normal_route, filtered_graph, speed, False)
int_km, int_eta = calculate_eta(intelligent_route, filtered_graph, speed, True)

# ---------------------------------
# STEP 9: MANUAL SIGNAL DENSITY
# ---------------------------------
def manual_signal_density(route, graph):
    manual_count = 0
    total_dist = 0

    for i in range(len(route) - 1):
        u, v = route[i], route[i + 1]
        edge = graph.get_edge_data(u, v)[0]
        total_dist += edge.get("length", 0)
        if graph.nodes[v]["signal"] == "manual":
            manual_count += 1

    dist_km = total_dist / 1000 if total_dist > 0 else 1
    density = manual_count / dist_km
    return manual_count, dist_km, density

n_manual, _, n_density = manual_signal_density(normal_route, filtered_graph)
i_manual, _, i_density = manual_signal_density(intelligent_route, filtered_graph)

# ---------------------------------
# STEP 10: RESULTS
# ---------------------------------
print("\n========== ROUTE COMPARISON ==========")

print("\nNormal Route (Blue)")
print(f"Distance              : {normal_km:.2f} km")
print(f"ETA                   : {normal_eta:.2f} min")
print(f"Manual Signals        : {n_manual}")
print(f"Manual Signal Density : {n_density:.2f} / km")

print("\nAnalyzed Route (Yellow)")
print(f"Distance              : {int_km:.2f} km")
print(f"ETA                   : {int_eta:.2f} min")
print(f"Manual Signals        : {i_manual}")
print(f"Manual Signal Density : {i_density:.2f} / km")

if i_density < n_density:
    print("\n✅ Analyzed route offers smoother travel with fewer manual signals.")
else:
    print("\n⚠ Normal route has fewer manual signals in this case.")

print("======================================")

# ---------------------------------
# STEP 11: VISUALIZATION
# ---------------------------------
node_colors = [
    "green" if filtered_graph.nodes[n]["signal"] == "automatic" else "red"
    for n in filtered_graph.nodes
]

fig, ax = ox.plot_graph(
    filtered_graph,
    node_color=node_colors,
    node_size=10,
    edge_linewidth=0.6,
    show=False,
    close=False
)

def plot_route(route, color, label):
    for i in range(len(route) - 1):
        u, v = route[i], route[i + 1]
        ax.plot(
            [filtered_graph.nodes[u]["x"], filtered_graph.nodes[v]["x"]],
            [filtered_graph.nodes[u]["y"], filtered_graph.nodes[v]["y"]],
            color=color,
            linewidth=3,
            label=label if i == 0 else ""
        )

plot_route(normal_route, "blue", "Normal Route")
plot_route(intelligent_route, "yellow", "Analyzed Route")

ax.scatter(
    filtered_graph.nodes[source]["x"],
    filtered_graph.nodes[source]["y"],
    c="purple", s=120, label="Source"
)

ax.scatter(
    filtered_graph.nodes[target]["x"],
    filtered_graph.nodes[target]["y"],
    c="orange", s=120, label="Destination"
)

ax.legend()
plt.show()