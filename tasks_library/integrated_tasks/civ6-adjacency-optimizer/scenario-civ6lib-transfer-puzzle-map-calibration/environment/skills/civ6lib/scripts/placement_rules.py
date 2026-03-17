"""District placement rules for Civ6 (Gathering Storm)."""

from dataclasses import dataclass
from enum import IntEnum, auto
from typing import Dict, List, Optional, Set, Tuple

from hex_utils import get_direction_to_neighbor, get_neighbors, hex_distance, is_adjacent


class DistrictType(IntEnum):
    NONE = 0
    CITY_CENTER = auto()
    CAMPUS = auto()
    HOLY_SITE = auto()
    THEATER_SQUARE = auto()
    COMMERCIAL_HUB = auto()
    HARBOR = auto()
    INDUSTRIAL_ZONE = auto()
    ENTERTAINMENT_COMPLEX = auto()
    WATER_PARK = auto()
    ENCAMPMENT = auto()
    AERODROME = auto()
    GOVERNMENT_PLAZA = auto()
    DIPLOMATIC_QUARTER = auto()
    PRESERVE = auto()
    AQUEDUCT = auto()
    DAM = auto()
    CANAL = auto()
    SPACEPORT = auto()
    NEIGHBORHOOD = auto()


DISTRICT_NAME_MAP: Dict[str, DistrictType] = {
    district.name: district for district in DistrictType if district != DistrictType.NONE
}


@dataclass
class Tile:
    x: int
    y: int
    terrain: str
    feature: Optional[str] = None
    is_hills: bool = False
    is_floodplains: bool = False
    river_edges: List[int] = None
    river_names: List[str] = None
    resource: Optional[str] = None
    resource_type: Optional[str] = None
    improvement: Optional[str] = None

    def __post_init__(self):
        if self.river_edges is None:
            self.river_edges = []
        if self.river_names is None:
            self.river_names = []

    @property
    def is_water(self) -> bool:
        return self.terrain in ("COAST", "OCEAN", "LAKE")

    @property
    def is_coast(self) -> bool:
        return self.terrain == "COAST"

    @property
    def is_lake(self) -> bool:
        return self.terrain == "LAKE"

    @property
    def is_mountain(self) -> bool:
        return self.terrain == "MOUNTAIN"

    @property
    def is_natural_wonder(self) -> bool:
        return self.feature is not None and "NATURAL_WONDER" in self.feature

    @property
    def has_river(self) -> bool:
        return len(self.river_edges) > 0

    @property
    def is_flat_land(self) -> bool:
        return not self.is_water and not self.is_mountain and not self.is_hills


MIN_CITY_DISTANCE_SAME_LANDMASS = 4
MIN_CITY_DISTANCE_DIFFERENT_LANDMASS = 3


def validate_city_distances(
    city_centers: List[Tuple[int, int]],
    tiles: Dict[Tuple[int, int], Tile],
) -> Tuple[bool, List[str]]:
    errors = []
    for i, city_a in enumerate(city_centers):
        for j, city_b in enumerate(city_centers):
            if j <= i:
                continue
            distance = hex_distance(city_a[0], city_a[1], city_b[0], city_b[1])
            same_landmass = _are_cities_on_same_landmass(city_a, city_b, tiles)
            min_distance = (
                MIN_CITY_DISTANCE_SAME_LANDMASS
                if same_landmass else MIN_CITY_DISTANCE_DIFFERENT_LANDMASS
            )
            if distance < min_distance:
                errors.append(
                    f"Cities at {city_a} and {city_b} are too close: "
                    f"distance={distance}, minimum={min_distance} "
                    f"({'same' if same_landmass else 'different'} landmass)"
                )
    return len(errors) == 0, errors


def _are_cities_on_same_landmass(
    city_a: Tuple[int, int],
    city_b: Tuple[int, int],
    tiles: Dict[Tuple[int, int], Tile],
) -> bool:
    tile_a = tiles.get(city_a)
    tile_b = tiles.get(city_b)

    if tile_a is None or tile_b is None:
        return True
    if tile_a.is_water or tile_b.is_water:
        return False

    visited = set()
    queue = [city_a]
    while queue:
        current = queue.pop(0)
        if current == city_b:
            return True
        if current in visited:
            continue
        visited.add(current)
        for nx, ny in get_neighbors(current[0], current[1]):
            if (nx, ny) in visited:
                continue
            neighbor_tile = tiles.get((nx, ny))
            if neighbor_tile is None:
                continue
            if not neighbor_tile.is_water:
                queue.append((nx, ny))
    return False


def calculate_max_specialty_districts(population: int) -> int:
    return 1 + (population - 1) // 3


def validate_district_count(
    placements: Dict[str, Tuple[int, int]],
    population: int,
) -> Tuple[bool, List[str]]:
    errors = []
    specialty_count = 0
    for district_name in placements:
        if district_name not in DISTRICT_NAME_MAP:
            continue
        district_type = DISTRICT_NAME_MAP[district_name]
        if district_type not in PlacementRules.NON_SPECIALTY_DISTRICTS:
            specialty_count += 1
    max_allowed = calculate_max_specialty_districts(population)
    if specialty_count > max_allowed:
        errors.append(
            f"Too many specialty districts: {specialty_count} placed, "
            f"but population {population} only allows {max_allowed} "
            f"(formula: 1 + floor(({population}-1)/3))"
        )
    return len(errors) == 0, errors


def validate_district_uniqueness(
    placements: Dict[str, Tuple[int, int]],
    city_id: str = "city",
    all_placements: Optional[Dict[str, Dict[str, Tuple[int, int]]]] = None,
) -> Tuple[bool, List[str]]:
    errors = []
    district_counts: Dict[str, int] = {}
    for district_name in placements:
        district_counts[district_name] = district_counts.get(district_name, 0) + 1

    for district_name, count in district_counts.items():
        if district_name not in DISTRICT_NAME_MAP:
            continue
        district_type = DISTRICT_NAME_MAP[district_name]
        if district_type in PlacementRules.ALLOW_MULTIPLE_PER_CITY:
            continue
        if count > 1:
            errors.append(
                f"Duplicate district in {city_id}: {district_name} placed {count} times "
                f"(only 1 allowed per city)"
            )

    if all_placements is not None:
        for district_type in PlacementRules.ONE_PER_CIVILIZATION:
            district_name = district_type.name
            civ_count = 0
            cities_with_district = []
            for cid, city_placements in all_placements.items():
                if district_name in city_placements:
                    civ_count += 1
                    cities_with_district.append(cid)
            if civ_count > 1:
                errors.append(
                    f"{district_name} can only be built once per civilization, "
                    f"but found in {civ_count} cities: {cities_with_district}"
                )

    return len(errors) == 0, errors


@dataclass
class PlacementResult:
    valid: bool
    errors: List[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class PlacementRules:
    WATER_DISTRICTS: Set[DistrictType] = {
        DistrictType.HARBOR,
        DistrictType.WATER_PARK,
    }

    FLAT_LAND_DISTRICTS: Set[DistrictType] = {
        DistrictType.AERODROME,
        DistrictType.SPACEPORT,
    }

    NO_CITY_CENTER_ADJACENT: Set[DistrictType] = {
        DistrictType.ENCAMPMENT,
        DistrictType.PRESERVE,
    }

    NON_SPECIALTY_DISTRICTS: Set[DistrictType] = {
        DistrictType.AQUEDUCT,
        DistrictType.DAM,
        DistrictType.CANAL,
        DistrictType.SPACEPORT,
        DistrictType.NEIGHBORHOOD,
        DistrictType.CITY_CENTER,
    }

    ALLOW_MULTIPLE_PER_CITY: Set[DistrictType] = {
        DistrictType.NEIGHBORHOOD,
        DistrictType.AQUEDUCT,
        DistrictType.DAM,
        DistrictType.CANAL,
        DistrictType.SPACEPORT,
    }

    ONE_PER_CIVILIZATION: Set[DistrictType] = {
        DistrictType.GOVERNMENT_PLAZA,
        DistrictType.DIPLOMATIC_QUARTER,
    }

    DESTRUCTIBLE_FEATURES: Set[str] = {
        "FEATURE_FOREST",
        "FEATURE_JUNGLE",
        "FEATURE_MARSH",
    }

    def __init__(
        self,
        tiles: Dict[Tuple[int, int], Tile],
        city_center: Tuple[int, int],
        population: int,
    ):
        self.tiles = tiles
        self.city_center = city_center
        self.population = population

    def get_tile(self, x: int, y: int) -> Optional[Tile]:
        return self.tiles.get((x, y))

    def validate_placement(
        self,
        district_type: DistrictType,
        x: int,
        y: int,
        existing_placements: Dict[Tuple[int, int], DistrictType],
    ) -> PlacementResult:
        errors: List[str] = []
        warnings: List[str] = []

        tile = self.get_tile(x, y)
        if tile is None:
            errors.append(f"No tile data at ({x}, {y})")
            return PlacementResult(valid=False, errors=errors)

        distance = hex_distance(x, y, self.city_center[0], self.city_center[1])
        if distance > 3:
            errors.append(f"Too far from City Center (distance {distance} > 3)")

        if tile.is_mountain:
            errors.append("Cannot place district on Mountain")
        if tile.is_natural_wonder:
            errors.append("Cannot place district on Natural Wonder")
        if tile.feature == "FEATURE_GEOTHERMAL_FISSURE":
            errors.append("Cannot place district on Geothermal Fissure")
        if (x, y) in existing_placements:
            errors.append(f"Tile already has district: {existing_placements[(x, y)].name}")
        if tile.resource_type in ("STRATEGIC", "LUXURY"):
            errors.append(f"Cannot place on {tile.resource_type.lower()} resource: {tile.resource}")

        if district_type in self.WATER_DISTRICTS:
            if not (tile.is_coast or tile.is_lake):
                errors.append(f"{district_type.name} must be on Coast or Lake")
            has_land_neighbor = False
            for nx, ny in get_neighbors(x, y):
                ntile = self.get_tile(nx, ny)
                if ntile and not ntile.is_water:
                    has_land_neighbor = True
                    break
            if not has_land_neighbor:
                errors.append(f"{district_type.name} must be adjacent to land")
        else:
            if tile.is_water:
                errors.append(f"{district_type.name} cannot be placed on water")

        if district_type in self.FLAT_LAND_DISTRICTS and not tile.is_flat_land:
            errors.append(f"{district_type.name} requires flat land (no hills, water, or mountains)")

        if district_type in self.NO_CITY_CENTER_ADJACENT:
            if hex_distance(x, y, self.city_center[0], self.city_center[1]) == 1:
                errors.append(f"{district_type.name} cannot be adjacent to City Center")

        if district_type == DistrictType.AQUEDUCT:
            errors.extend(self._validate_aqueduct(x, y))
        if district_type == DistrictType.DAM:
            errors.extend(self._validate_dam(x, y))
        if district_type == DistrictType.CANAL:
            errors.extend(self._validate_canal(x, y, existing_placements))

        if tile.feature in self.DESTRUCTIBLE_FEATURES:
            warnings.append(f"Placing here will destroy {tile.feature}")
        if tile.resource_type == "BONUS":
            warnings.append(f"Placing here will destroy bonus resource: {tile.resource}")

        return PlacementResult(valid=len(errors) == 0, errors=errors, warnings=warnings)

    def _validate_aqueduct(self, x: int, y: int) -> List[str]:
        errors = []
        tile = self.get_tile(x, y)
        if hex_distance(x, y, self.city_center[0], self.city_center[1]) != 1:
            errors.append("Aqueduct must be adjacent to City Center")
            return errors

        fresh_water_sources = []
        for nx, ny in get_neighbors(x, y):
            ntile = self.get_tile(nx, ny)
            if ntile is None:
                continue
            if ntile.is_mountain:
                fresh_water_sources.append(("Mountain", nx, ny))
            elif ntile.is_lake:
                fresh_water_sources.append(("Lake", nx, ny))
            elif ntile.feature == "FEATURE_OASIS":
                fresh_water_sources.append(("Oasis", nx, ny))
            elif ntile.has_river:
                fresh_water_sources.append(("River", nx, ny))

        if tile.has_river:
            fresh_water_sources.append(("River", x, y))

        if not fresh_water_sources:
            errors.append("Aqueduct requires adjacent fresh water (Mountain, River, Lake, or Oasis)")

        if fresh_water_sources:
            cc_direction = get_direction_to_neighbor(x, y, self.city_center[0], self.city_center[1])
            cc_neighbor = (self.city_center[0], self.city_center[1])
            non_cc_sources = [
                source for source in fresh_water_sources
                if (source[1], source[2]) != cc_neighbor and not (source[0] == "River" and cc_direction in tile.river_edges)
            ]
            if not non_cc_sources and len(fresh_water_sources) == 1 and fresh_water_sources[0][0] == "River":
                if set(tile.river_edges) == {cc_direction}:
                    errors.append("Aqueduct 'No U-Turn' rule: Fresh water cannot only be on City Center edge")

        return errors

    def _validate_dam(self, x: int, y: int) -> List[str]:
        errors = []
        tile = self.get_tile(x, y)
        if not tile.is_floodplains:
            errors.append("Dam must be on Floodplains")
            return errors
        if len(tile.river_edges) < 2:
            errors.append("Dam requires river to traverse at least 2 hex edges")
        return errors

    def _validate_canal(
        self,
        x: int,
        y: int,
        existing_placements: Dict[Tuple[int, int], DistrictType],
    ) -> List[str]:
        errors = []
        adjacent_city_center = False
        adjacent_water_tiles = []

        for nx, ny in get_neighbors(x, y):
            if (nx, ny) == self.city_center or existing_placements.get((nx, ny)) == DistrictType.CITY_CENTER:
                adjacent_city_center = True

            ntile = self.get_tile(nx, ny)
            if ntile is not None and (ntile.is_water or ntile.is_lake):
                adjacent_water_tiles.append((nx, ny))

        if not adjacent_water_tiles:
            errors.append("Canal must be adjacent to at least one water body (Coast/Ocean/Lake)")
            return errors

        if adjacent_city_center and len(adjacent_water_tiles) >= 1:
            return errors

        if len(adjacent_water_tiles) >= 2:
            for i, (wx1, wy1) in enumerate(adjacent_water_tiles):
                for wx2, wy2 in adjacent_water_tiles[i + 1:]:
                    if not is_adjacent(wx1, wy1, wx2, wy2):
                        return errors
            errors.append("Canal must connect separate water bodies (adjacent water tiles are the same body)")
            return errors

        errors.append("Canal must connect City Center to water OR connect two separate water bodies")
        return errors


def get_placement_rules(
    tiles: Dict[Tuple[int, int], Tile],
    city_center: Tuple[int, int],
    population: int,
) -> PlacementRules:
    return PlacementRules(tiles, city_center, population)
