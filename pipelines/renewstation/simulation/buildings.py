"""The 17 virtual buildings of the district and their equipment ranges."""

from dataclasses import dataclass

# Order matters: each building gets a running number used to seed its randomness.
BUILDING_COUNTS = {
    "Hospital": 1,
    "House": 10,
    "Industry": 2,
    "Office": 3,
    "School": 1,
}

# Ranges in kW
SPECIAL_EQUIPMENT_RANGE = {
    "Hospital": (2.5, 8),
    "House": (0.15, 0.8),
    "Industry": (5, 18),
    "School": (0.8, 3.5),
    "Office": (0.8, 4.5),
}
LIGHTING_RANGE = {
    "Hospital": (1.2, 3.5),
    "House": (0.08, 0.4),
    "Industry": (1, 4),
    "School": (0.3, 1.8),
    "Office": (0.4, 2.2),
}
HVAC_RANGE = {
    "Hospital": (2.5, 7),
    "House": (0.2, 1.3),
    "Industry": (1.5, 6),
    "School": (0.6, 3),
    "Office": (0.7, 3.5),
}
# Number of people
OCCUPANCY_RANGE = {
    "Hospital": (50, 200),
    "House": (1, 4),
    "Industry": (10, 100),
    "School": (50, 500),
    "Office": (5, 50),
}

HOUSE_PROFILES = {
    "summer_vacation": {"vacation_months": [7, 8], "has_ac": True, "heating_type": "electric"},
    "winter_vacation": {"vacation_months": [12], "has_ac": False, "heating_type": "gas"},
    "always_home_ac": {"vacation_months": [], "has_ac": True, "heating_type": "electric"},
    "always_home_no_ac": {"vacation_months": [], "has_ac": False, "heating_type": "electric"},
    "work_from_home": {
        "vacation_months": [8], "has_ac": True, "heating_type": "heatpump", "high_daytime_usage": True,
    },
    "student_house": {
        "vacation_months": [7, 8, 12], "has_ac": False, "heating_type": "gas", "low_equipment": True,
    },
    "large_family": {
        "vacation_months": [7], "has_ac": True, "heating_type": "electric", "high_equipment": True,
    },
}
# Profile picked by the building's running number (number 1 is the hospital)
PROFILE_SEQUENCE = [
    "summer_vacation", "summer_vacation", "winter_vacation", "always_home_ac", "always_home_ac",
    "always_home_no_ac", "always_home_no_ac", "work_from_home", "work_from_home", "work_from_home",
    "student_house", "student_house", "large_family", "large_family", "large_family",
]


@dataclass(frozen=True)
class Building:
    name: str        # e.g. "House3"
    type: str        # e.g. "House"
    number: int      # running number across the district, starting at 1


def buildings() -> list[Building]:
    result, number = [], 0
    for building_type, count in BUILDING_COUNTS.items():
        for i in range(1, count + 1):
            number += 1
            name = building_type if count == 1 else f"{building_type}{i}"
            result.append(Building(name, building_type, number))
    return result


def building_names() -> list[str]:
    return [b.name for b in buildings()]


def house_profile(number: int) -> dict:
    index = number - 1
    name = PROFILE_SEQUENCE[index] if index < len(PROFILE_SEQUENCE) else "summer_vacation"
    return {**HOUSE_PROFILES[name], "name": name}
