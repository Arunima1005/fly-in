"""Space-time pathfinding for routing one drone at a time around the
zones and connections that earlier drones have already claimed."""

from __future__ import annotations

import heapq
from dataclasses import dataclass

from model import Connection, Graph, Zone, ZoneType

# How many turns it costs to enter each zone type. BLOCKED is left out on
# purpose: a blocked zone is never offered as a destination at all, so
# nothing should ever need to look up its cost.
MOVE_COST: dict[ZoneType, int] = {
    ZoneType.NORMAL: 1,
    ZoneType.PRIORITY: 1,
    ZoneType.RESTRICTED: 2,
}

# A drone's full turn-by-turn position. path_events[t] is where the drone
# is at turn t: a Zone if it's standing somewhere, or a Connection if it's
# mid-transit toward a restricted zone.
PathEvents = list[Zone | Connection]


class NoPathFoundError(Exception):
    """Raised when a drone cannot reach the end zone within the search
    horizon, given what earlier drones have already reserved."""


class ReservationTable:
    """Remembers which zones and connections are already claimed, turn by
    turn, by drones that have already been planned."""

    def __init__(self, graph: Graph) -> None:
        if graph.start_zone is None or graph.end_zone is None:
            raise ValueError("graph needs a start_zone and an end_zone")
        self._graph = graph
        # The start and end zones never run out of room (the subject says
        # so explicitly), so they're simply never checked or recorded.
        self._unlimited = {graph.start_zone.name, graph.end_zone.name}
        self._zone_use: dict[tuple[str, int], int] = {}
        self._link_use: dict[tuple[tuple[str, str], int], int] = {}

    @staticmethod
    def _link_key(connection: Connection) -> tuple[str, str]:
        # Sorting the two names means "a-b" and "b-a" land on the same key.
        a, b = connection.zone_a.name, connection.zone_b.name
        return (a, b) if a < b else (b, a)

    def zone_has_room(self, zone: Zone, turn: int) -> bool:
        """Is there a free slot in this zone at the end of this turn?"""
        if zone.name in self._unlimited:
            return True
        used = self._zone_use.get((zone.name, turn), 0)
        return used < zone.max_drones

    def link_has_room(self, connection: Connection, turn: int) -> bool:
        """Is there a free slot on this connection during this turn?"""
        used = self._link_use.get((self._link_key(connection), turn), 0)
        return used < connection.max_link_capacity

    def commit(self, path_events: PathEvents) -> None:
        """Record everything one drone's finished plan uses, turn by turn.

        path_events[t] is the drone's position at turn t (index 0 = turn 0,
        the moment it starts at the start zone).
        """
        for turn in range(1, len(path_events)):
            here = path_events[turn]
            there_before = path_events[turn - 1]

            if isinstance(here, Connection):
                # First turn of a restricted transit: on the wire, no zone.
                self._reserve_link(here, turn)
            elif isinstance(there_before, Connection):
                # Second turn of that same transit: still the wire, then
                # the drone actually lands in the zone this turn.
                self._reserve_link(there_before, turn)
                self._reserve_zone(here, turn)
            else:
                # An ordinary move, or simply waiting in the same zone.
                if there_before.name != here.name:
                    connection = self._graph.get_connection(
                        there_before.name, here.name,
                    )
                    if connection is None:
                        raise ValueError(
                            f"no connection {there_before.name}-{here.name}"
                        )
                    self._reserve_link(connection, turn)
                self._reserve_zone(here, turn)

    def _reserve_zone(self, zone: Zone, turn: int) -> None:
        if zone.name in self._unlimited:
            return
        key = (zone.name, turn)
        self._zone_use[key] = self._zone_use.get(key, 0) + 1

    def _reserve_link(self, connection: Connection, turn: int) -> None:
        key = (self._link_key(connection), turn)
        self._link_use[key] = self._link_use.get(key, 0) + 1


@dataclass
class _Step:
    """How we reached one zone during the search: where we came from, and
    whether that was an ordinary move, a 2-turn restricted transit, or
    simply waiting in place."""

    from_zone: str | None
    connection: Connection | None
    turns_used: int  # 1 for a normal move or a wait, 2 for restricted


def find_path_for_one_drone(
    graph: Graph,
    reservations: ReservationTable,
    start_turn: int = 0,
    horizon: int = 500,
) -> PathEvents:
    """Find the earliest turn one drone can reach the end zone, given
    everything already in `reservations`. Returns the drone's full
    turn-by-turn plan. Raises NoPathFoundError if nothing works within
    `horizon` turns (a generous safety limit, not a real map size).
    """
    assert graph.start_zone is not None and graph.end_zone is not None
    start_name = graph.start_zone.name
    end_name = graph.end_zone.name

    # earliest[zone_name] = the earliest turn we've confirmed a drone can
    # be standing there. previous[zone_name] = how it got there.
    earliest: dict[str, int] = {start_name: start_turn}
    previous: dict[str, _Step] = {start_name: _Step(None, None, 0)}

    # The heap always gives us the zone with the smallest confirmed turn
    # next — exactly like plain Dijkstra, just reading "turn" where you'd
    # normally read "cost".
    to_visit: list[tuple[int, str]] = [(start_turn, start_name)]
    finalized: set[str] = set()

    while to_visit:
        turn_here, name = heapq.heappop(to_visit)
        if name in finalized:
            continue  # a stale, already-beaten entry left over in the heap
        finalized.add(name)

        if name == end_name:
            return _build_path_events(graph, previous, earliest, end_name)

        here = graph.get_zone(name)
        assert here is not None
        for neighbor, connection in graph.get_neighbors(here):
            if neighbor.zone_type is ZoneType.BLOCKED:
                continue  # never a valid place to stop

            cost = MOVE_COST[neighbor.zone_type]
            earliest_arrival = _earliest_legal_arrival(
                reservations, connection, neighbor, turn_here, cost, horizon,
            )
            if earliest_arrival is None:
                continue  # never became free within the horizon

            if earliest_arrival < earliest.get(neighbor.name, horizon + 1):
                earliest[neighbor.name] = earliest_arrival
                previous[neighbor.name] = _Step(name, connection, cost)
                heapq.heappush(to_visit, (earliest_arrival, neighbor.name))

    raise NoPathFoundError(f"no route to {end_name} within {horizon} turns")


def _earliest_legal_arrival(
    reservations: ReservationTable,
    connection: Connection,
    destination: Zone,
    depart_from_turn: int,
    cost: int,
    horizon: int,
) -> int | None:
    """Scan forward for the first arrival turn at which this move is
    actually allowed — i.e. "wait until there's room" folded directly into
    the move itself, instead of modeling waiting as its own search step."""
    candidate_arrival = depart_from_turn + cost
    while candidate_arrival <= horizon:
        if cost == 1:
            link_ok = reservations.link_has_room(connection, candidate_arrival)
        else:
            # A restricted move occupies the connection for both of its
            # turns, and it's all-or-nothing: both must be free together.
            link_ok = (
                reservations.link_has_room(connection, candidate_arrival - 1)
                and reservations.link_has_room(connection, candidate_arrival)
            )
        zone_ok = reservations.zone_has_room(destination, candidate_arrival)
        if link_ok and zone_ok:
            return candidate_arrival
        candidate_arrival += 1
    return None


def _build_path_events(
    graph: Graph,
    previous: dict[str, _Step],
    earliest: dict[str, int],
    end_name: str,
) -> PathEvents:
    """Walk `previous` backwards from the end zone to the start zone, then
    expand it into one entry per turn: path_events[t] is where the drone is
    at turn t. A repeated zone means it waited there; a Connection entry
    means it's mid-transit toward a restricted zone."""
    chain: list[tuple[str, _Step]] = []
    name = end_name
    while True:
        step = previous[name]
        chain.append((name, step))
        if step.from_zone is None:
            break
        name = step.from_zone
    chain.reverse()  # now start -> ... -> end

    start_name = chain[0][0]
    start_zone = graph.get_zone(start_name)
    assert start_zone is not None
    path_events: PathEvents = [start_zone]  # index 0 == earliest[start_name]

    for i in range(1, len(chain)):
        zone_name, step = chain[i]
        zone = graph.get_zone(zone_name)
        assert zone is not None and step.connection is not None
        arrive_here = earliest[zone_name]

        # The move itself takes `step.turns_used` turns and ends exactly
        # at `arrive_here`, so it must have started at this turn. Every
        # turn before that, the drone is still waiting in the previous
        # zone -- so pad with repeats until we reach that point.
        move_starts_at = arrive_here - step.turns_used + 1
        while len(path_events) < move_starts_at:
            path_events.append(path_events[-1])

        if step.turns_used == 1:
            path_events.append(zone)
        else:
            path_events.append(step.connection)  # mid-transit turn
            path_events.append(zone)              # arrival turn

    return path_events


def plan_all_drones(graph: Graph, nb_drones: int) -> list[PathEvents]:
    """Plan every drone one at a time (prioritized planning): each drone's
    search sees everything the earlier drones already committed."""
    reservations = ReservationTable(graph)
    all_paths: list[PathEvents] = []
    for _ in range(nb_drones):
        path_events = find_path_for_one_drone(graph, reservations)
        reservations.commit(path_events)
        all_paths.append(path_events)
    return all_paths