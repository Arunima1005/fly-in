*This project has been created as part of the 42 curriculum by archowdh.*

# Fly-in

## Description

Fly-in is a drone routing simulator. A fleet of drones starts in a start zone
and has to reach an end zone through a network of connected zones, in as few
simulation turns as possible.

The network is read from a map file. Zones have a type (normal, priority,
restricted or blocked), a capacity (how many drones can be in the zone at the
same time) and an optional color. Connections between zones also have a
capacity (how many drones can use the connection in the same turn).

The program:

- parses and validates the map file, with clear error messages,
- plans a path for every drone with a custom Dijkstra implementation,
- runs the simulation turn by turn while respecting every capacity and
  movement rule,
- prints the moves of each turn in the required format, and
- can show the simulation in a colored terminal view or in a pygame window.

The graph, the pathfinding and the scheduling are written from scratch. No
graph library (networkx, graphlib, ...) is used.

## Instructions

### Requirements

- Python 3.10 or later
- [uv](https://docs.astral.sh/uv/) (recommended), or pip
- Dependencies: `pydantic` (data models) and `pygame` (only for `--visual`)

### Installation

```bash
make install        # runs: uv sync
```

Without uv:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pydantic pygame
```

### Running

```bash
make run                                   # choose a map from a menu
make run MAP=maps/easy/01_linear_path.txt  # run one map directly
make run-verbose MAP=maps/hard/01_maze_nightmare.txt
make run-visual  MAP=maps/hard/01_maze_nightmare.txt
```

Or call the program directly:

```bash
python3 -m src [--file MAP] [--verbose] [--visual]
```

| Option | Effect |
|---|---|
| *(none)* | Plain output in the required format, one line per turn |
| `--file MAP` | Use this map file. Without it, a menu lets you pick a difficulty and a map from `maps/` (in the terminal, or in the window with `--visual`) |
| `--verbose` | Colored, detailed terminal output: every drone's position each turn, with zone names in their map colors, plus a summary |
| `--visual` | Opens the pygame window, starting with a map menu (or directly with the `--file` map). The turns are still printed in the terminal |
| `-h` | Show the help |

The flags can be combined, for example `--visual --verbose`.

In the pygame window:

| Where | Key / action | Effect |
|---|---|---|
| Map menu | Click a button | Choose a difficulty, then a map (**Back** returns to the difficulties) |
| Map menu | **Esc** | Back to the difficulties, or quit from the first screen |
| Simulation | **Space** | Pause / resume |
| Simulation | **Up** / **Down** | Animation speed (0.5x, 1x, 2x, 4x, 8x) |
| Simulation | **M** | Back to the map menu, to run another map |
| Simulation | **Esc** | Quit |
| Anywhere | Close button | Quit |

### Other Makefile rules

| Rule | Effect |
|---|---|
| `make debug` | Run the program in the Python debugger (`pdb`) |
| `make clean` | Remove `__pycache__`, `.mypy_cache` and other temporary files |
| `make lint` | Run `flake8` and `mypy` |

### Map file format

```
nb_drones: 5
start_hub: hub 0 0 [color=green]
end_hub: goal 10 10 [color=yellow]
hub: roof1 3 4 [zone=restricted color=red]
hub: corridorA 4 3 [zone=priority color=green max_drones=2]
hub: obstacleX 5 5 [zone=blocked color=gray]
connection: hub-roof1
connection: corridorA-tunnelB [max_link_capacity=2]
# comments start with '#'
```

- The first line must be `nb_drones: <positive integer>`.
- Zones: `start_hub:`, `end_hub:` or `hub:`, then a name, integer `x y`
  coordinates and optional metadata in brackets: `zone=` (default `normal`),
  `color=` and `max_drones=` (default 1).
- Connections: `connection: <zone1>-<zone2>`, with optional
  `[max_link_capacity=N]` (default 1). Connections go both ways.

## Example

Input (`maps/easy/02_simple_fork.txt`):

```
nb_drones: 4

start_hub: start 0 0 [color=green]
hub: junction 1 0 [color=yellow max_drones=2]
hub: path_a 2 1 [color=blue]
hub: path_b 2 -1 [color=blue]
end_hub: goal 3 0 [color=red]

connection: start-junction [max_link_capacity=2]
connection: junction-path_a
connection: junction-path_b
connection: path_a-goal
connection: path_b-goal
```

Output of `python3 -m src --file maps/easy/02_simple_fork.txt`:

```
D1-junction D2-junction
D1-path_a D2-path_b D3-junction D4-junction
D1-goal D2-goal D3-path_a D4-path_b
D3-goal D4-goal
```

Each line is one turn. `D<ID>-<zone>` means the drone moved to that zone.
Drones that do not move are left out. The two drones share the junction
(capacity 2), then split over the two equal branches, so all four arrive in
4 turns.

A drone heading into a **restricted** zone needs 2 turns. During the first
turn it is shown on the connection, as `D<ID>-<from>-<to>`:

```
nb_drones: 2
start_hub: start 0 0
hub: tunnel 1 0 [zone=restricted]
end_hub: goal 2 0
connection: start-tunnel
connection: tunnel-goal
```

```
D1-start-tunnel
D1-tunnel
D1-goal D2-start-tunnel
D2-tunnel
D2-goal
```

D2 waits at the start until the tunnel (capacity 1) is free again.

With `--verbose`, the same fork map gives:

```
Turn 01  D1-junction D2-junction D3-start D4-start
Turn 02  D1-path_a D2-path_b D3-junction D4-junction
Turn 03  D1-goal D2-goal D3-path_a D4-path_b
Turn 04  D1-goal D2-goal D3-goal D4-goal

✓ SIMULATION COMPLETED
  4 turns
```

### Error handling

Invalid maps stop the program with a message that gives the line and the
cause, and exit code 1. Some examples:

```
Error: Line 1: First line must be nb_drones: <number>
Error: Line 3: Invalid zone type 'lava'
Error: Line 3: max_drones must be positive
Error: Line 4: Duplicate zone name: a
Error: Line 5: Duplicate connection e - s
Error: Line 4: Unknown zone x
Error: Line 3: only one start_hub is allowed
Error: Map is missing end_hub
Error: No path found from start to end
Error: Map file not found: maps/easy/missing.txt
```

## Algorithm explanation

The solution has two separate steps: **planning** a path for each drone once,
and **scheduling** the moves turn by turn.

### 1. Path planning: Dijkstra with tie-breaking

Every drone gets a full path from start to end, computed once before the
simulation starts (`Dijkstra.find_path` in `src/dijkstra.py`).

- **Edge cost** = the cost of entering the destination zone: 1 turn for
  normal and priority zones, 2 turns for restricted zones. Blocked zones are
  never entered.
- The search uses a priority queue (`heapq`) ordered by
  `(cost, -priority_count)`. When two routes cost the same, the one passing
  through **more priority zones** wins, as the subject asks.
- **Spreading drones over paths.** Drones are planned one after another. A
  running counter records how many already-planned drones pass through each
  zone, and each zone adds a small extra cost of `0.01 × usage`. This never
  makes a longer route win, but when several routes are equally short, later
  drones take the less used one. On the simple fork map this sends half the
  drones down each branch and saves 2 turns.

**Design decision.** I tested larger congestion weights (0.1 to 2.0) to
force drones onto more different routes. The drones did spread out more, but
the total number of turns went up on the hard maps (for example 26 → 30 on
*Ultimate challenge*), because the alternative routes go through restricted
zones and are slower than waiting in line. Without the small weight (0), the
simple fork took 6 turns instead of 4 and the challenger map 67 instead of 43.
The small tie-breaking weight gave the best results on every map.

### 2. Turn scheduling

Each turn (`Simulation.run_turn` in `src/simulation.py`):

1. **Drones in flight land.** A drone that took off toward a restricted zone
   last turn must arrive now. Its place in the destination was already
   reserved at take-off, so it can never get stuck on the connection. It
   still counts against the connection's capacity for this turn.
2. **Every other drone asks to move** to the next zone on its path.
3. **Moves are accepted one at a time** (`select_moves`), drones furthest
   along their path first. Before accepting a move, the program checks the
   connection capacity and the destination's free space. After accepting it,
   it updates the counts right away: the zone the drone left gets a free
   place in the same turn, as the subject requires. The passes repeat until
   nothing changes, so a drone can also follow a drone that was accepted
   later in the pass.
4. Drones whose move is refused simply **wait** in place.

The start and end zones have no capacity limit.

**Deadlocks** cannot happen: every path only leads toward the end zone, and
the drone furthest ahead always moves first, so a queue always drains from
the front.

### Complexity

With **V** zones, **E** connections, **D** drones, **L** the path length and
**T** the number of turns:

- **Planning:** one Dijkstra per drone, `O(D · (E + V) log V)`. Paths are
  computed once and stored, not recalculated each turn.
- **Scheduling:** each turn checks the waiting drones. The repeated passes
  are `O(D²)` in the worst case, usually close to `O(D)`, so
  `O(T · D²)` in the worst case overall.
- **Memory:** the graph `O(V + E)` plus the stored paths `O(D · L)`.

As a test, the *Ultimate challenge* map with **1000 drones** finished in
about 3 seconds, using about 30 MB.

### Results on the provided maps

| Map | Drones | Turns | Target |
|---|---|---|---|
| Linear path | 2 | 4 | ≤ 6 |
| Simple fork | 4 | 4 | ≤ 8 |
| Basic capacity | 4 | 4 | ≤ 6 |
| Dead end trap | 5 | 8 | ≤ 12 |
| Circular loop | 6 | 15 | ≤ 15 |
| Priority puzzle | 5 | 8 | ≤ 12 |
| Maze nightmare | 8 | 13 | ≤ 30 |
| Capacity hell | 12 | 16 | ≤ 35 |
| Ultimate challenge | 15 | 26 | ≤ 45 |
| **The Impossible Dream** (challenger) | 25 | **43** | beat 45 |

On *Maze nightmare*, every route passes through the connection
`maze_c2-bottleneck`, which lets only one drone through per turn. The first
drone needs 6 moves and the other 7 arrive one per turn after it, so 13 turns
is the best possible result on that map.

## Visual representation

### Terminal (`--verbose`)

- A header with the number of drones and the start and end zones.
- One line per turn with **every** drone's position, as `D<ID>-<zone>`.
  Each entry uses two colors:
  - the **drone ID** shows the drone's state: magenta for drones still
    waiting at the start, white for drones on the way, red for drones in
    flight toward a restricted zone, green for delivered drones;
  - the **zone name** uses the **color from the map file** (for example
    `[color=gold]`). Zones without a color, or with a color name the
    terminal does not know, are shown in white. `black` is shown as gray so
    it stays readable on a dark terminal.
- A summary with the total number of turns.

This makes waiting visible: in the plain output a waiting drone is left out,
in the verbose view you can see exactly where it is. The map colors make it
easy to match the terminal output with the map file and the pygame window.

The terminal uses 256-color codes, so colors like orange, gold or brown can
look slightly different from the pygame window.

### Graphical window (`--visual`)

- **Map menu:** the window opens with a menu. Buttons for the four
  difficulties, then one button per map file, with a **Back** button. The
  button under the mouse is highlighted. After a simulation, **M** brings
  you back here, so several maps can be compared without restarting the
  program. Each map always starts again from turn 0.
- **The map:** zones are drawn at their coordinates and scaled to fit the
  window. Each zone uses the **color from the map file**. The start and end
  zones have an extra ring around them.
- **Shapes show zone types:** circle = normal, square = restricted,
  diamond = priority, triangle = blocked. A legend in the corner explains
  this.
- **Drones** are drawn as drone icons with a small **ID badge**, so each
  drone can be followed and matched with the terminal output.
- **Smooth animation:** drones glide between zones, with a short pause after
  each turn. A drone flying to a restricted zone stops **halfway along the
  connection** after its first turn, which shows the 2-turn cost.
- **Stats panel:** number of drones and zones, the current turn, the
  status (Running, Paused or Finished) and the animation speed.
- **Controls:** Space to pause and resume, Up / Down to change the speed
  (0.5x, 1x, 2x, 4x, 8x), M for the map menu, Esc to quit. A hint at the top
  of the window lists these keys. The speed only changes the animation,
  not the simulation or its output. The window can be resized, and the map
  is re-centered and re-scaled.
- The terminal keeps printing each turn while the window is open, so the
  picture and the required output always match.

Together, these show *why* a drone waits (a full zone or connection), how
drones share capacity, and the real cost of restricted zones, which is hard
to see from the text output alone.

## Project structure

```
src/
  __main__.py         command line options, error handling, chooses the mode
  model.py            Zone, Connection, Drone, Graph (pydantic models)
  parse.py            MapParser: reads and validates map files
  dijkstra.py         Dijkstra: path planning with tie-breaking
  simulation.py       Simulation: turn scheduling and terminal output
  map_selector.py     MapSelector: map menu in the terminal
  map_selection_ui.py MapSelectionUI: map menu in the pygame window
  visualizer.py       Visualizer: pygame window
maps/                 provided maps (easy, medium, hard, challenger)
assets/               drone image for the pygame window
```

## Resources

- [Dijkstra's algorithm (Wikipedia)](https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm)
- [Introduction to A* and pathfinding, Red Blob Games](https://www.redblobgames.com/pathfinding/a-star/introduction.html)
- [Python `heapq` documentation](https://docs.python.org/3/library/heapq.html)
- [Python `argparse` documentation](https://docs.python.org/3/library/argparse.html)
- [pydantic documentation](https://docs.pydantic.dev/)
- [pygame documentation](https://www.pygame.org/docs/)
- [mypy documentation](https://mypy.readthedocs.io/) and
  [flake8 documentation](https://flake8.pycqa.org/)
- **AI usage:** an AI assistant (Claude) was used to discuss design
  decisions for the project, to learn about the pathfinding algorithm and
  pygame, to help write the pytest tests and this README, and to help debug
  some issues.
