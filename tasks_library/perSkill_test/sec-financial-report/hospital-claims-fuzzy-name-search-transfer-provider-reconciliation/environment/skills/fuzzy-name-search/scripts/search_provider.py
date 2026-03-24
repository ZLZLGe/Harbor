#!/usr/bin/env python3

import argparse
import re
from difflib import SequenceMatcher

import pandas as pd


def normalize(text):
    return re.sub(r"[^a-z0-9]+", "", str(text).lower())


def score(term, candidate):
    return SequenceMatcher(None, normalize(term), normalize(candidate)).ratio()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keywords", required=True)
    parser.add_argument("--input", default="/root/provider_master.csv")
    parser.add_argument("--topk", type=int, default=5)
    args = parser.parse_args()

    providers = pd.read_csv(args.input)
    ranked = []
    for index, row in providers.iterrows():
        candidate_score = max(
            score(args.keywords, row["provider_name"]),
            score(args.keywords, f"{row['provider_name']} {row['city']}"),
        )
        ranked.append((candidate_score, index))

    for rank, (candidate_score, index) in enumerate(
        sorted(ranked, reverse=True)[: args.topk], start=1
    ):
        row = providers.iloc[index]
        print(f"** Rank {rank} (score = {candidate_score:.3f}) **")
        print(f"  provider_id: {row['provider_id']}")
        print(f"  provider_name: {row['provider_name']}")
        print(f"  network_id: {row['network_id']}")
        print(f"  network_name: {row['network_name']}")
        print()


if __name__ == "__main__":
    main()
