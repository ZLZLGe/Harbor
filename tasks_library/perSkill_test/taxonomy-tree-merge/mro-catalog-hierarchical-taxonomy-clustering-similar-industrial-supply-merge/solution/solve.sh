#!/bin/bash
set -euo pipefail

cat > /tmp/mro_taxonomy_solver.py <<'PY'
#!/usr/bin/env python3

import os
import re
from pathlib import Path

import pandas as pd


DATA_DIR = Path(os.getenv("DATA_DIR", "/root/data"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/root/output"))


PHRASE_REPLACEMENTS = {
    "wire and cable": "wire cable",
    "wire & cable": "wire cable",
    "conduit and fittings": "conduit fittings",
    "conduit & fittings": "conduit fittings",
    "liquid tight": "liquidtight",
    "cut off": "cutoff",
    "cut-off": "cutoff",
    "v-belts": "v belts",
    "v-belt": "v belt",
    "motors & drives": "motors drives",
    "magnets & clamps": "magnetic clamps",
    "hook-up": "hook up",
    "jobber length": "jobber",
    "er70s 6": "er70s6",
    "er70s-6": "er70s6",
    "threadlockers": "threadlocker",
    "epoxies": "epoxy",
    "silicone sealants": "silicone sealant",
    "hard hats": "hard hat",
    "gloves": "glove",
    "respirators": "respirator",
    "connectors": "connector",
    "breakers": "breaker",
    "fittings": "fitting",
    "bits": "bit",
    "mills": "mill",
    "assemblies": "assembly",
    "bearings": "bearing",
    "belts": "belt",
    "towels": "towel",
    "degreasers": "degreaser",
    "bags": "bag",
    "trucks": "truck",
    "cabinets": "cabinet",
    "helmets": "helmet",
}


PRODUCT_RULES = [
    {
        "keywords": ["hex", "screw"],
        "leaf": "hex cap screw",
        "levels": (
            "fastener | hardware",
            "threaded | assembly",
            "bolt | screw",
            "hex | head",
            "cap | screw",
        ),
    },
    {
        "keywords": ["hex", "bolt"],
        "leaf": "hex bolt",
        "levels": (
            "fastener | hardware",
            "threaded | assembly",
            "bolt | screw",
            "hex | head",
            "hex | bolt",
        ),
    },
    {
        "keywords": ["concrete", "anchor"],
        "leaf": "concrete anchor",
        "levels": (
            "fastener | hardware",
            "anchor | insert",
            "masonry | mount",
            "concrete | fixing",
            "anchor | screw",
        ),
    },
    {
        "keywords": ["split", "lock", "washer"],
        "leaf": "split lock washer",
        "levels": (
            "fastener | hardware",
            "retention | spacing",
            "washer | shim",
            "split | lock",
            "spring | washer",
        ),
    },
    {
        "keywords": ["nitrile", "glove"],
        "leaf": "nitrile glove",
        "levels": (
            "safety | ppe",
            "hand | protection",
            "chemical | barrier",
            "disposable | exam",
            "nitrile | glove",
        ),
    },
    {
        "keywords": ["hard", "hat"],
        "leaf": "hard hat",
        "levels": (
            "safety | ppe",
            "head | impact",
            "jobsite | shell",
            "full | brim",
            "hard | hat",
        ),
    },
    {
        "keywords": ["half", "mask"],
        "leaf": "half mask respirator",
        "levels": (
            "safety | ppe",
            "airway | defense",
            "reusable | mask",
            "filter | cartridge",
            "half | respirator",
        ),
    },
    {
        "keywords": ["thhn", "wire"],
        "leaf": "thhn wire",
        "levels": (
            "electrical | wiring",
            "cable | conductor",
            "building | wire",
            "thermoplastic | nylon",
            "thhn | copper",
        ),
    },
    {
        "keywords": ["miniature", "circuit", "breaker"],
        "leaf": "miniature circuit breaker",
        "levels": (
            "electrical | wiring",
            "control | protection",
            "branch | interrupt",
            "panel | safety",
            "miniature | breaker",
        ),
    },
    {
        "keywords": ["liquidtight", "straight", "connector"],
        "leaf": "liquidtight straight connector",
        "levels": (
            "electrical | wiring",
            "conduit | entry",
            "liquidtight | fitting",
            "straight | body",
            "cable | connector",
        ),
    },
    {
        "keywords": ["cobalt", "drill", "bit"],
        "leaf": "cobalt drill bit",
        "levels": (
            "cutting | tooling",
            "holemaking | drill",
            "cobalt | alloy",
            "jobber | length",
            "twist | bit",
        ),
    },
    {
        "keywords": ["carbide", "end", "mill"],
        "leaf": "carbide end mill",
        "levels": (
            "cutting | tooling",
            "milling | cutter",
            "carbide | flute",
            "square | end",
            "end | mill",
        ),
    },
    {
        "keywords": ["thin", "cutoff", "wheel"],
        "leaf": "thin cutoff wheel",
        "levels": (
            "cutting | tooling",
            "abrasive | sawing",
            "resin | bonded",
            "thin | profile",
            "cutoff | wheel",
        ),
    },
    {
        "keywords": ["two", "wire", "hose"],
        "leaf": "two wire hose",
        "levels": (
            "fluid | power",
            "hydraulic | transfer",
            "reinforced | hose",
            "two | wire",
            "pressure | line",
        ),
    },
    {
        "keywords": ["filter", "regulator", "lubricator"],
        "leaf": "filter regulator lubricator",
        "levels": (
            "fluid | power",
            "air | preparation",
            "filter | regulator",
            "lubrication | unit",
            "frl | assembly",
        ),
    },
    {
        "keywords": ["jic", "male", "adapter"],
        "leaf": "jic male adapter",
        "levels": (
            "fluid | power",
            "pressure | fitting",
            "jic | interface",
            "male | adapter",
            "tube | connector",
        ),
    },
    {
        "keywords": ["tefc", "motor"],
        "leaf": "tefc motor",
        "levels": (
            "motion | drive",
            "motor | gearbox",
            "induction | drive",
            "enclosed | cooled",
            "general | motor",
        ),
    },
    {
        "keywords": ["sealed", "ball", "bearing"],
        "leaf": "sealed ball bearing",
        "levels": (
            "motion | drive",
            "bearing | support",
            "rolling | element",
            "sealed | race",
            "ball | bearing",
        ),
    },
    {
        "keywords": ["classical", "v", "belt"],
        "leaf": "classical v belt",
        "levels": (
            "motion | drive",
            "belt | coupling",
            "power | transfer",
            "classical | section",
            "v | belt",
        ),
    },
    {
        "keywords": ["roll", "towel"],
        "leaf": "roll towel",
        "levels": (
            "janitorial | cleaning",
            "wiper | tissue",
            "absorbent | paper",
            "roll | dispenser",
            "hand | towel",
        ),
    },
    {
        "keywords": ["citrus", "degreaser"],
        "leaf": "citrus degreaser",
        "levels": (
            "janitorial | cleaning",
            "surface | cleaner",
            "oil | removal",
            "citrus | base",
            "degreaser | fluid",
        ),
    },
    {
        "keywords": ["contractor", "bag"],
        "leaf": "contractor bag",
        "levels": (
            "janitorial | cleaning",
            "waste | liner",
            "heavy | gauge",
            "jobsite | cleanup",
            "contractor | bag",
        ),
    },
    {
        "keywords": ["steel", "deck", "platform", "truck"],
        "leaf": "steel deck platform truck",
        "levels": (
            "material | handling",
            "cart | truck",
            "platform | mover",
            "steel | deck",
            "warehouse | transport",
        ),
    },
    {
        "keywords": ["shelf", "bin", "system"],
        "leaf": "shelf bin system",
        "levels": (
            "material | handling",
            "bin | shelving",
            "small | parts",
            "open | front",
            "pick | storage",
        ),
    },
    {
        "keywords": ["welded", "storage", "cabinet"],
        "leaf": "welded storage cabinet",
        "levels": (
            "material | handling",
            "cabinet | locker",
            "enclosed | storage",
            "welded | steel",
            "shop | cabinet",
        ),
    },
    {
        "keywords": ["er70s6"],
        "leaf": "er70s6 wire",
        "levels": (
            "welding | joining",
            "wire | rod",
            "solid | electrode",
            "mild | steel",
            "mig | filler",
        ),
    },
    {
        "keywords": ["auto", "darkening", "helmet"],
        "leaf": "auto darkening helmet",
        "levels": (
            "welding | joining",
            "helmet | screen",
            "arc | shielding",
            "auto | darkening",
            "weld | hood",
        ),
    },
    {
        "keywords": ["magnetic", "clamp"],
        "leaf": "magnetic welding clamp",
        "levels": (
            "welding | joining",
            "clamp | fixture",
            "magnetic | hold",
            "angle | setup",
            "weld | clamp",
        ),
    },
    {
        "keywords": ["blue", "threadlocker"],
        "leaf": "blue threadlocker",
        "levels": (
            "adhesive | sealant",
            "threadlocker | retaining",
            "medium | strength",
            "removable | cure",
            "anaerobic | liquid",
        ),
    },
    {
        "keywords": ["steel", "repair", "putty"],
        "leaf": "steel repair putty",
        "levels": (
            "adhesive | sealant",
            "epoxy | repair",
            "metal | rebuild",
            "putty | compound",
            "structural | patch",
        ),
    },
    {
        "keywords": ["gasket", "maker"],
        "leaf": "gasket maker",
        "levels": (
            "adhesive | sealant",
            "silicone | gasketing",
            "rtv | cure",
            "engine | sealing",
            "form | gasket",
        ),
    },
]


def load_sources():
    grainger = pd.read_csv(DATA_DIR / "grainger_mro_catalog.csv").rename(
        columns={"taxonomy_path": "raw_path"}
    )
    grainger["supplier"] = "grainger"

    mcmaster = pd.read_csv(DATA_DIR / "mcmaster_mro_catalog.csv").rename(
        columns={"catalog_path": "raw_path"}
    )
    mcmaster["supplier"] = "mcmaster"

    fastenal = pd.read_csv(DATA_DIR / "fastenal_mro_catalog.csv").rename(
        columns={"web_hierarchy": "raw_path"}
    )
    fastenal["supplier"] = "fastenal"

    return pd.concat(
        [
            grainger[["supplier", "raw_path"]],
            mcmaster[["supplier", "raw_path"]],
            fastenal[["supplier", "raw_path"]],
        ],
        ignore_index=True,
    )


def normalize_path(path):
    text = str(path).strip()
    text = text.replace(" / ", " > ").replace(" :: ", " > ")
    text = text.replace("&", " and ")
    text = text.replace("-", " ")
    text = re.sub(r"\s+", " ", text)
    parts = [normalize_segment(part) for part in text.split(" > ")]
    parts = [part for part in parts if part and part not in {"catalog", "products", "shop"}]
    return " > ".join(parts)


def normalize_segment(segment):
    text = segment.lower().strip()
    text = text.replace("&", " and ")
    text = text.replace("-", " ")
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    for src, dst in PHRASE_REPLACEMENTS.items():
        text = text.replace(src, dst)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def classify_path(path):
    for rule in PRODUCT_RULES:
        if all(keyword in path for keyword in rule["keywords"]):
            return rule["leaf"], rule["levels"]

    leaf = path.split(" > ")[-1].strip()
    fallback_levels = (
        "misc | industrial",
        "general | supply",
        "unclassified | branch",
        "source | review",
        "manual | check",
    )
    return leaf, fallback_levels


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = load_sources()
    df["supplier_category_path"] = df["raw_path"].map(normalize_path)
    df["source_depth"] = df["supplier_category_path"].map(lambda x: x.count(" > ") + 1)

    classified = df["supplier_category_path"].map(classify_path)
    df["normalized_leaf"] = classified.map(lambda x: x[0])
    levels_df = pd.DataFrame(
        classified.map(lambda x: x[1]).tolist(),
        columns=[f"procurement_family_l{i}" for i in range(1, 6)],
    )

    result = pd.concat(
        [
            df[["supplier", "supplier_category_path", "source_depth", "normalized_leaf"]],
            levels_df,
        ],
        axis=1,
    ).sort_values(["supplier", "supplier_category_path"]).reset_index(drop=True)

    result.to_csv(OUTPUT_DIR / "mro_taxonomy_mapping.csv", index=False)

    hierarchy_cols = [f"procurement_family_l{i}" for i in range(1, 6)]
    hierarchy = (
        result[hierarchy_cols]
        .drop_duplicates()
        .sort_values(hierarchy_cols, kind="stable")
        .reset_index(drop=True)
    )
    hierarchy.to_csv(OUTPUT_DIR / "mro_taxonomy_hierarchy.csv", index=False)


if __name__ == "__main__":
    main()
PY

python3 /tmp/mro_taxonomy_solver.py
