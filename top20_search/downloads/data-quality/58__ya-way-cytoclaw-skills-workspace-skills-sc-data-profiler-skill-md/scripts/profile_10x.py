#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path

import numpy as np


def _load_adata(input_path: Path):
    import scanpy as sc

    if input_path.is_file() and input_path.suffix == ".h5":
        adata = sc.read_10x_h5(str(input_path))
        adata.var_names_make_unique()
        return adata

    if input_path.is_dir():
        adata = sc.read_10x_mtx(str(input_path), var_names="gene_symbols", cache=False)
        adata.var_names_make_unique()
        return adata

    raise ValueError(f"Unsupported input path: {input_path}")


def _to_dense_vector(x):
    if hasattr(x, "A1"):
        return x.A1
    if hasattr(x, "toarray"):
        return np.asarray(x.toarray()).ravel()
    return np.asarray(x).ravel()


def _quantiles(values):
    return {
        "q25": float(np.quantile(values, 0.25)),
        "q50": float(np.quantile(values, 0.50)),
        "q90": float(np.quantile(values, 0.90)),
    }


def main():
    parser = argparse.ArgumentParser(description="Profile raw 10x scRNA-seq matrix.")
    parser.add_argument("--input", required=True, help="Absolute path to raw 10x dir or .h5")
    parser.add_argument("--out", default="", help="Optional output JSON path")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")

    adata = _load_adata(input_path)

    n_cells = int(adata.n_obs)
    genes_per_cell = _to_dense_vector((adata.X > 0).sum(axis=1))

    mito_mask = adata.var_names.str.upper().str.startswith("MT-")
    if mito_mask.sum() == 0:
        mito_pct = np.zeros(n_cells, dtype=float)
    else:
        mito_counts = _to_dense_vector(adata.X[:, mito_mask].sum(axis=1))
        total_counts = _to_dense_vector(adata.X.sum(axis=1))
        mito_pct = np.divide(
            mito_counts,
            np.maximum(total_counts, 1e-12),
            out=np.zeros_like(mito_counts, dtype=float),
            where=total_counts > 0,
        ) * 100.0

    q = _quantiles(mito_pct)
    # Conservative candidate generation for adaptive choice.
    candidates = sorted(set([5, 8, 10, int(round(min(max(q["q90"], 5), 20)))]))

    result = {
        "input": str(input_path),
        "n_cells": n_cells,
        "n_genes_median_per_cell": float(np.median(genes_per_cell)),
        "mito_pct_quantiles": q,
        "recommended_mito_cutoff_candidates": candidates,
    }

    if args.out:
        out_path = Path(args.out).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
