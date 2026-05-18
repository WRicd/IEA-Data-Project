REGION_ROWS = [
    ("World", "World", "", "World", False),
    ("China", "China", "CHN", "Asia Pacific", True),
    ("Europe", "Europe", "", "Europe", False),
    ("North America", "North America", "", "North America", False),
    ("United States", "United States", "USA", "North America", True),
    ("USA", "United States", "USA", "North America", True),
    ("Asia Pacific", "Asia Pacific", "", "Asia Pacific", False),
    ("Central and South America", "Central and South America", "", "Central and South America", False),
    ("Africa", "Africa", "", "Africa", False),
    ("Middle East", "Middle East", "", "Middle East", False),
    ("India", "India", "IND", "Asia Pacific", True),
    ("Japan", "Japan", "JPN", "Asia Pacific", True),
    ("Korea", "Korea", "KOR", "Asia Pacific", True),
    ("Canada", "Canada", "CAN", "North America", True),
    ("Mexico", "Mexico", "MEX", "North America", True),
    ("Brazil", "Brazil", "BRA", "Central and South America", True),
    ("Australia", "Australia", "AUS", "Asia Pacific", True),
    ("United Arab Emirates", "Middle East", "ARE", "Middle East", True),
    ("France", "Europe", "FRA", "Europe", True),
    ("Germany", "Europe", "DEU", "Europe", True),
    ("United Kingdom", "Europe", "GBR", "Europe", True),
    ("Norway", "Europe", "NOR", "Europe", True),
    ("Netherlands", "Europe", "NLD", "Europe", True),
    ("Italy", "Europe", "ITA", "Europe", True),
    ("Sweden", "Europe", "SWE", "Europe", True),
    ("Denmark", "Europe", "DNK", "Europe", True),
    ("Belgium", "Europe", "BEL", "Europe", True),
]

REGION_MAP = {raw: common for raw, common, *_ in REGION_ROWS}
REGION_GROUP_MAP = {raw: group for raw, _, __, group, ___ in REGION_ROWS}


def common_region(raw_region):
    if raw_region is None:
        return None
    return REGION_MAP.get(str(raw_region), str(raw_region))


def region_group(raw_region):
    if raw_region is None:
        return None
    return REGION_GROUP_MAP.get(str(raw_region), common_region(raw_region))
