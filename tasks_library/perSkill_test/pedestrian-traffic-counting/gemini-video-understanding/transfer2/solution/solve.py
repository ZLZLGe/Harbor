import pandas as pd

INPUT_PATH = "/root/gate_counts.csv"
OUTPUT_PATH = "/root/transfer2_comparison.csv"


def main() -> None:
    df = pd.read_csv(INPUT_PATH)
    ped = df[df["kind"] == "pedestrian"].copy()

    rows = []
    for camera, group in ped.groupby("camera"):
        in_ids = set(group.loc[group["direction"] == "IN", "person_id"].astype(str))
        out_ids = set(group.loc[group["direction"] == "OUT", "person_id"].astype(str))

        high_conf_ids = set(group.loc[group["confidence"] >= 0.9, "person_id"].astype(str))

        in_count = len(in_ids)
        out_count = len(out_ids)
        rows.append(
            {
                "camera": camera,
                "in_count": in_count,
                "out_count": out_count,
                "net_flow": in_count - out_count,
                "high_conf_unique": len(high_conf_ids),
            }
        )

    out = pd.DataFrame(rows).sort_values("camera").reset_index(drop=True)
    out.to_csv(OUTPUT_PATH, index=False)


if __name__ == "__main__":
    main()
