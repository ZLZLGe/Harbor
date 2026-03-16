"""District adjacency bonus calculations for Civ6 (Gathering Storm)."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from hex_utils import get_neighbors
from placement_rules import DistrictType, Tile


@dataclass
class AdjacencyRule:
    sources: List[str]
    bonus_per: int
    count_required: int = 1


@dataclass
class AdjacencyResult:
    total_bonus: int
    breakdown: Dict[str, Dict[str, Any]] = field(default_factory=dict)


CAMPUS_RULES = [
    AdjacencyRule(["FEATURE_GEOTHERMAL_FISSURE"], bonus_per=2, count_required=1),
    AdjacencyRule(["FEATURE_REEF"], bonus_per=2, count_required=1),
    AdjacencyRule(["GREAT_BARRIER_REEF"], bonus_per=2, count_required=1),
    AdjacencyRule(["MOUNTAIN"], bonus_per=1, count_required=1),
    AdjacencyRule(["FEATURE_JUNGLE"], bonus_per=1, count_required=2),
    AdjacencyRule(["DISTRICT"], bonus_per=1, count_required=2),
]

HOLY_SITE_RULES = [
    AdjacencyRule(["NATURAL_WONDER"], bonus_per=2, count_required=1),
    AdjacencyRule(["MOUNTAIN"], bonus_per=1, count_required=1),
    AdjacencyRule(["FEATURE_FOREST"], bonus_per=1, count_required=2),
    AdjacencyRule(["DISTRICT"], bonus_per=1, count_required=2),
]

THEATER_SQUARE_RULES = [
    AdjacencyRule(["WONDER"], bonus_per=2, count_required=1),
    AdjacencyRule(["ENTERTAINMENT_COMPLEX", "WATER_PARK"], bonus_per=2, count_required=1),
    AdjacencyRule(["DISTRICT"], bonus_per=1, count_required=2),
]

COMMERCIAL_HUB_RULES = [
    AdjacencyRule(["HARBOR"], bonus_per=2, count_required=1),
    AdjacencyRule(["DISTRICT"], bonus_per=1, count_required=2),
]

HARBOR_RULES = [
    AdjacencyRule(["CITY_CENTER"], bonus_per=2, count_required=1),
    AdjacencyRule(["COASTAL_RESOURCE"], bonus_per=1, count_required=1),
    AdjacencyRule(["DISTRICT"], bonus_per=1, count_required=2),
]

INDUSTRIAL_ZONE_RULES = [
    AdjacencyRule(["AQUEDUCT", "BATH", "DAM", "CANAL"], bonus_per=2, count_required=1),
    AdjacencyRule(["QUARRY"], bonus_per=1, count_required=1),
    AdjacencyRule(["STRATEGIC_RESOURCE"], bonus_per=1, count_required=1),
    AdjacencyRule(["MINE"], bonus_per=1, count_required=2),
    AdjacencyRule(["LUMBER_MILL"], bonus_per=1, count_required=2),
    AdjacencyRule(["DISTRICT"], bonus_per=1, count_required=2),
]

DISTRICT_ADJACENCY_RULES: Dict[DistrictType, List[AdjacencyRule]] = {
    DistrictType.CAMPUS: CAMPUS_RULES,
    DistrictType.HOLY_SITE: HOLY_SITE_RULES,
    DistrictType.THEATER_SQUARE: THEATER_SQUARE_RULES,
    DistrictType.COMMERCIAL_HUB: COMMERCIAL_HUB_RULES,
    DistrictType.HARBOR: HARBOR_RULES,
    DistrictType.INDUSTRIAL_ZONE: INDUSTRIAL_ZONE_RULES,
}

DISTRICTS_FOR_ADJACENCY: Set[DistrictType] = {
    DistrictType.CAMPUS,
    DistrictType.HOLY_SITE,
    DistrictType.THEATER_SQUARE,
    DistrictType.COMMERCIAL_HUB,
    DistrictType.HARBOR,
    DistrictType.INDUSTRIAL_ZONE,
    DistrictType.GOVERNMENT_PLAZA,
    DistrictType.ENTERTAINMENT_COMPLEX,
    DistrictType.WATER_PARK,
    DistrictType.ENCAMPMENT,
    DistrictType.AERODROME,
    DistrictType.PRESERVE,
    DistrictType.DIPLOMATIC_QUARTER,
    DistrictType.CITY_CENTER,
    DistrictType.AQUEDUCT,
    DistrictType.DAM,
    DistrictType.CANAL,
    DistrictType.NEIGHBORHOOD,
    DistrictType.SPACEPORT,
}

IZ_SPECIAL_BONUS_DISTRICTS: Set[DistrictType] = {
    DistrictType.AQUEDUCT,
    DistrictType.DAM,
    DistrictType.CANAL,
}

HARBOR_SPECIAL_BONUS_DISTRICTS: Set[DistrictType] = {
    DistrictType.CITY_CENTER,
}

COMMERCIAL_HUB_SPECIAL_BONUS_DISTRICTS: Set[DistrictType] = {
    DistrictType.HARBOR,
}

THEATER_SQUARE_SPECIAL_BONUS_DISTRICTS: Set[DistrictType] = {
    DistrictType.ENTERTAINMENT_COMPLEX,
    DistrictType.WATER_PARK,
}

SPECIALTY_DISTRICTS = DISTRICTS_FOR_ADJACENCY

DESTRUCTIBLE_FEATURES: Set[str] = {
    "FEATURE_FOREST",
    "FEATURE_JUNGLE",
    "FEATURE_MARSH",
}


class AdjacencyCalculator:
    def __init__(self, tiles: Dict[Tuple[int, int], Tile]):
        self.tiles = tiles

    def apply_destruction(
        self,
        placements: Dict[Tuple[int, int], DistrictType],
    ) -> Dict[Tuple[int, int], Tile]:
        modified = {}
        for coord, tile in self.tiles.items():
            if coord in placements:
                district_type = placements[coord]
                if district_type == DistrictType.CITY_CENTER:
                    modified[coord] = tile
                else:
                    modified[coord] = Tile(
                        x=tile.x,
                        y=tile.y,
                        terrain=tile.terrain,
                        feature=None if tile.feature in DESTRUCTIBLE_FEATURES else tile.feature,
                        is_hills=tile.is_hills,
                        is_floodplains=tile.is_floodplains,
                        river_edges=list(tile.river_edges),
                        river_names=list(tile.river_names),
                        resource=None if tile.resource_type == "BONUS" else tile.resource,
                        resource_type=None if tile.resource_type == "BONUS" else tile.resource_type,
                        improvement=None,
                    )
            else:
                modified[coord] = tile
        return modified

    def count_rule_sources(
        self,
        x: int,
        y: int,
        rule: AdjacencyRule,
        tiles: Dict[Tuple[int, int], Tile],
        placements: Dict[Tuple[int, int], DistrictType],
        current_district: Optional[DistrictType] = None,
    ) -> Tuple[int, List[str]]:
        count = 0
        sources: List[str] = []

        for nx, ny in get_neighbors(x, y):
            ntile = tiles.get((nx, ny))
            for source_type in rule.sources:
                matched = False
                if ntile is None and (nx, ny) not in placements:
                    continue

                if ntile is not None:
                    if source_type == "MOUNTAIN" and ntile.is_mountain:
                        count += 1
                        sources.append(f"Mountain@({nx},{ny})")
                        matched = True
                    elif source_type == "NATURAL_WONDER" and ntile.is_natural_wonder:
                        count += 1
                        sources.append(f"NaturalWonder@({nx},{ny})")
                        matched = True
                    elif ntile.feature and source_type in ntile.feature:
                        count += 1
                        sources.append(f"{source_type}@({nx},{ny})")
                        matched = True
                    elif ntile.feature and ntile.feature == source_type:
                        count += 1
                        sources.append(f"{source_type}@({nx},{ny})")
                        matched = True
                    elif ntile.improvement and ntile.improvement.upper() == source_type:
                        count += 1
                        sources.append(f"{source_type}@({nx},{ny})")
                        matched = True
                    elif source_type == "STRATEGIC_RESOURCE" and ntile.resource_type == "STRATEGIC":
                        count += 1
                        sources.append(f"Strategic({ntile.resource})@({nx},{ny})")
                        matched = True
                    elif source_type == "COASTAL_RESOURCE":
                        if ntile.is_water and ntile.resource:
                            count += 1
                            sources.append(f"CoastalResource({ntile.resource})@({nx},{ny})")
                            matched = True

                if (nx, ny) in placements:
                    adj_district = placements[(nx, ny)]
                    if source_type == adj_district.name or source_type == adj_district.name.upper():
                        count += 1
                        sources.append(f"{adj_district.name}@({nx},{ny})")
                        matched = True
                    elif source_type == "ENTERTAINMENT_COMPLEX" and adj_district == DistrictType.ENTERTAINMENT_COMPLEX:
                        count += 1
                        sources.append(f"EntertainmentComplex@({nx},{ny})")
                        matched = True
                    elif source_type == "WATER_PARK" and adj_district == DistrictType.WATER_PARK:
                        count += 1
                        sources.append(f"WaterPark@({nx},{ny})")
                        matched = True
                    elif source_type == "CITY_CENTER" and adj_district == DistrictType.CITY_CENTER:
                        count += 1
                        sources.append(f"CityCenter@({nx},{ny})")
                        matched = True
                    elif source_type == "HARBOR" and adj_district == DistrictType.HARBOR:
                        count += 1
                        sources.append(f"Harbor@({nx},{ny})")
                        matched = True
                    elif source_type == "DISTRICT" and adj_district in SPECIALTY_DISTRICTS:
                        skip = False
                        if current_district == DistrictType.INDUSTRIAL_ZONE and adj_district in IZ_SPECIAL_BONUS_DISTRICTS:
                            skip = True
                        elif current_district == DistrictType.HARBOR and adj_district in HARBOR_SPECIAL_BONUS_DISTRICTS:
                            skip = True
                        elif current_district == DistrictType.COMMERCIAL_HUB and adj_district in COMMERCIAL_HUB_SPECIAL_BONUS_DISTRICTS:
                            skip = True
                        elif current_district == DistrictType.THEATER_SQUARE and adj_district in THEATER_SQUARE_SPECIAL_BONUS_DISTRICTS:
                            skip = True
                        if not skip:
                            count += 1
                            sources.append(f"District({adj_district.name})@({nx},{ny})")
                            matched = True

                if matched:
                    break

        return count, sources

    def calculate_district_adjacency(
        self,
        district_type: DistrictType,
        x: int,
        y: int,
        tiles: Dict[Tuple[int, int], Tile],
        placements: Dict[Tuple[int, int], DistrictType],
    ) -> AdjacencyResult:
        rules = DISTRICT_ADJACENCY_RULES.get(district_type, [])
        if not rules:
            return AdjacencyResult(total_bonus=0)

        tile = tiles.get((x, y))
        if tile is None:
            return AdjacencyResult(total_bonus=0)

        total = 0
        breakdown: Dict[str, Dict[str, Any]] = {}

        if district_type == DistrictType.COMMERCIAL_HUB and tile.has_river:
            total += 2
            breakdown["RIVER"] = {"count": 1, "bonus": 2, "sources": ["OnRiver"]}

        for rule in rules:
            count, sources = self.count_rule_sources(x, y, rule, tiles, placements, district_type)
            if count == 0:
                continue
            if rule.count_required == 1:
                bonus = count * rule.bonus_per
            else:
                bonus = (count // rule.count_required) * rule.bonus_per
            if bonus > 0:
                breakdown["+".join(rule.sources)] = {
                    "count": count,
                    "bonus": bonus,
                    "count_required": rule.count_required,
                    "bonus_per": rule.bonus_per,
                    "sources": sources,
                }
                total += bonus

        return AdjacencyResult(total_bonus=total, breakdown=breakdown)

    def calculate_total_adjacency(
        self,
        placements: Dict[Tuple[int, int], DistrictType],
    ) -> Tuple[int, Dict[str, AdjacencyResult]]:
        modified_tiles = self.apply_destruction(placements)
        total = 0
        per_district: Dict[str, AdjacencyResult] = {}
        for (x, y), district_type in placements.items():
            if district_type == DistrictType.CITY_CENTER:
                continue
            result = self.calculate_district_adjacency(
                district_type, x, y, modified_tiles, placements
            )
            total += result.total_bonus
            per_district[f"{district_type.name}@({x},{y})"] = result
        return total, per_district


def get_adjacency_calculator(
    tiles: Dict[Tuple[int, int], Tile],
) -> AdjacencyCalculator:
    return AdjacencyCalculator(tiles)
