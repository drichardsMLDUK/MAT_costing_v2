from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, TypedDict

import yaml

# -----------------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
PRODUCT_FILE = DATA_DIR / "product.yaml"
MATERIALS_FILE = DATA_DIR / "materials.yaml"
ARRAY_DESIGNS_FILE = DATA_DIR / "array_designs.yaml"


# -----------------------------------------------------------------------------
# Product model
# -----------------------------------------------------------------------------
@dataclass
class Product:
    """Core product configuration for the MAT array."""

    name: str = "Default MAT Array"

    # Core configuration
    cells_per_string: int = 20
    strings_per_array: int = 4

    # Finance
    exchange_rate_gbp_per_usd: float = 0.8  # example default

    # Geometry (all in mm)
    cell_height_mm: float = 6.6
    gap_between_cells_mm: float = 1.0
    positive_end_gap_mm: float = 5.0
    negative_end_gap_mm: float = 5.0

    @property
    def cells_per_array(self) -> int:
        """Total number of cells in the full array."""
        return self.cells_per_string * self.strings_per_array

    @property
    def total_string_length_mm(self) -> float:
        """
        Total physical length of one string [mm].

        Model:
        length = positive_end_gap +
                 negative_end_gap +
                 cells_per_string * cell_height +
                 (cells_per_string - 1) * gap_between_cells
        """
        n = max(self.cells_per_string, 0)
        gaps = max(n - 1, 0)
        return (
            self.positive_end_gap_mm
            + self.negative_end_gap_mm
            + n * self.cell_height_mm
            + gaps * self.gap_between_cells_mm
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a plain dict suitable for YAML."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Product":
        """Create a Product from a dict (e.g. loaded from YAML)."""
        return cls(**data)


def ensure_data_dir() -> None:
    """Make sure the data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_default_product() -> Product:
    """Default configuration for a new project."""
    return Product()


def load_product() -> Product:
    """
    Load the product configuration from product.yaml.
    If the file doesn't exist or is invalid, return a default Product.
    """
    ensure_data_dir()

    if not PRODUCT_FILE.exists():
        return get_default_product()

    try:
        with PRODUCT_FILE.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return Product.from_dict(data)
    except Exception:
        # Fallback to default if there's any issue with the YAML
        return get_default_product()


def save_product(product: Product) -> None:
    """Save the product configuration to product.yaml."""
    ensure_data_dir()
    with PRODUCT_FILE.open("w", encoding="utf-8") as f:
        yaml.safe_dump(product.to_dict(), f, sort_keys=False)


# -----------------------------------------------------------------------------
# Materials model (generic, YAML-based)
# -----------------------------------------------------------------------------

class MaterialItem(TypedDict, total=False):
    """
    Generic material entry.

    Not all keys are used by every category. Common keys:
    - id, name
    - unit, unit_cost_usd, notes

    Silver Ribbon-specific fields:
    - width_mm, thickness_mm, density_g_cm3
    - price_per_g, price_currency

    Other categories may add:
    - unit_cost_gbp
    - roll_length_value, roll_length_unit, roll_cost_usd, roll_cost_gbp
    - num_welds, price/currency fields, etc.
    """
    id: str
    name: str

    # Generic / legacy
    unit: str
    unit_cost_usd: float
    notes: str

    # Silver Ribbon-specific
    width_mm: float
    thickness_mm: float
    density_g_cm3: float
    price_per_g: float
    price_currency: str


MaterialsDB = Dict[str, List[MaterialItem]]

MATERIAL_CATEGORIES: List[str] = [
    "Silver Ribbon",
    "Diodes",
    "Weld heads",
    "Lamination",
    "Tapes",
    "Misc",
    "Packaging",
]


def get_default_materials() -> MaterialsDB:
    """Default empty materials structure with all categories present."""
    return {category: [] for category in MATERIAL_CATEGORIES}


def ensure_materials_file() -> None:
    """
    Ensure materials.yaml exists with at least the default structure.

    If the file is missing, we create one with empty lists for each category.
    """
    ensure_data_dir()

    if not MATERIALS_FILE.exists():
        default_data = get_default_materials()
        with MATERIALS_FILE.open("w", encoding="utf-8") as f:
            yaml.safe_dump(default_data, f, sort_keys=False)


def load_materials() -> MaterialsDB:
    """
    Load the materials database from materials.yaml.

    Ensures:
    - File exists (created if missing)
    - All expected categories exist as lists
    """
    ensure_materials_file()

    try:
        with MATERIALS_FILE.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        data = {}

    # Make sure it's a dict
    if not isinstance(data, dict):
        data = {}

    # Ensure all categories exist
    for category in MATERIAL_CATEGORIES:
        data.setdefault(category, [])

        # Make sure each category is a list
        if not isinstance(data[category], list):
            data[category] = []

    return data  # type: ignore[return-value]


def save_materials(materials: MaterialsDB) -> None:
    """Save the materials database back to materials.yaml."""
    ensure_data_dir()

    # Ensure all categories exist before saving
    for category in MATERIAL_CATEGORIES:
        materials.setdefault(category, [])

    with MATERIALS_FILE.open("w", encoding="utf-8") as f:
        yaml.safe_dump(materials, f, sort_keys=False)


# -----------------------------------------------------------------------------
# Array Designs model
# -----------------------------------------------------------------------------

class ArrayDesign(TypedDict, total=False):
    """
    Represents a single array design.

    Fields:
    - name: human-readable design name
    - num_cells: number of cells in the array
    - eff_am15_percent, eff_am0_percent: cell efficiencies in %
    - cell_height_mm, gap_between_cells_mm, positive_end_gap_mm, negative_end_gap_mm
    - blocking_tab_length1_mm, blocking_tab_length2_mm
    - negative_end_silver_id, negative_end_width_mm, negative_end_length_mm
    - negative_bar_silver_id, negative_bar_width_mm, negative_bar_length_mm
    """
    name: str
    num_cells: int

    eff_am15_percent: float
    eff_am0_percent: float

    cell_height_mm: float
    gap_between_cells_mm: float
    positive_end_gap_mm: float
    negative_end_gap_mm: float

    blocking_tab_length1_mm: float
    blocking_tab_length2_mm: float

    negative_end_silver_id: str
    negative_end_width_mm: float
    negative_end_length_mm: float

    negative_bar_silver_id: str
    negative_bar_width_mm: float
    negative_bar_length_mm: float


def ensure_array_designs_file() -> None:
    """Ensure array_designs.yaml exists; initialise as empty list if missing."""
    ensure_data_dir()

    if not ARRAY_DESIGNS_FILE.exists():
        with ARRAY_DESIGNS_FILE.open("w", encoding="utf-8") as f:
            yaml.safe_dump([], f, sort_keys=False)


def load_array_designs() -> List[ArrayDesign]:
    """Load all array designs from array_designs.yaml."""
    ensure_array_designs_file()

    try:
        with ARRAY_DESIGNS_FILE.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or []
    except Exception:
        data = []

    if not isinstance(data, list):
        data = []

    # We don't enforce schema here; just return list of dicts
    return data  # type: ignore[return-value]


def save_array_designs(designs: List[ArrayDesign]) -> None:
    """Save the list of array designs back to array_designs.yaml."""
    ensure_data_dir()
    with ARRAY_DESIGNS_FILE.open("w", encoding="utf-8") as f:
        yaml.safe_dump(designs, f, sort_keys=False)
