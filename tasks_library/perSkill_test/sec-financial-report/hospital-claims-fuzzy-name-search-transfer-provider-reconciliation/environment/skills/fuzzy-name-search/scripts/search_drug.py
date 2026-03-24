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
    parser.add_argument("--input", default="/root/drug_catalog.csv")
    parser.add_argument("--topk", type=int, default=5)
    args = parser.parse_args()

    drugs = pd.read_csv(args.input)
    ranked = []
    for index, row in drugs.iterrows():
        candidate_score = max(
            score(args.keywords, row["canonical_name"]),
            score(args.keywords, row["brand_name"]),
            score(args.keywords, f"{row['canonical_name']} {row['brand_name']}"),
        )
        ranked.append((candidate_score, index))

    for rank, (candidate_score, index) in enumerate(
        sorted(ranked, reverse=True)[: args.topk], start=1
    ):
        row = drugs.iloc[index]
        print(f"** Rank {rank} (score = {candidate_score:.3f}) **")
        print(f"  drug_code: {row['drug_code']}")
        print(f"  canonical_name: {row['canonical_name']}")
        print(f"  brand_name: {row['brand_name']}")
        print()


if __name__ == "__main__":
    main()
