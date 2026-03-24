#!/bin/bash

set -e

mkdir -p /root/workspace

cat > /root/workspace/triangle_shape_functions.py <<'EOF'
#!/usr/bin/env python3

import json
import tomllib

from sympy import Matrix, Rational, expand, simplify, sympify, symbols


x, y = symbols("x y")


def _to_exact(value):
    if isinstance(value, int):
        return Rational(value)
    return simplify(sympify(str(value), rational=True))


def _to_fraction_string(value):
    return str(simplify(value))


def _derive_case(nodes):
    interpolation_matrix = Matrix([[1, px, py] for px, py in nodes])

    shape_functions = []
    gradient_matrix = []
    for node_index in range(3):
        rhs = Matrix([1 if row_index == node_index else 0 for row_index in range(3)])
        a_i, b_i, c_i = interpolation_matrix.LUsolve(rhs)
        shape_function = simplify(expand(a_i + b_i * x + c_i * y))
        shape_functions.append(shape_function)
        gradient_matrix.append(
            [
                _to_fraction_string(shape_function.diff(x)),
                _to_fraction_string(shape_function.diff(y)),
            ]
        )

    signed_double_area = (
        (nodes[1][0] - nodes[0][0]) * (nodes[2][1] - nodes[0][1])
        - (nodes[1][1] - nodes[0][1]) * (nodes[2][0] - nodes[0][0])
    )
    area = simplify(abs(signed_double_area) / 2)

    return area, shape_functions, gradient_matrix


def derive_triangle_shape_data(filepath: str) -> dict:
    with open(filepath, "rb") as handle:
        payload = tomllib.load(handle)

    result = {"cases": {}}

    for case in payload["cases"]:
        nodes = [(_to_exact(px), _to_exact(py)) for px, py in case["nodes"]]
        area, shape_functions, gradient_matrix = _derive_case(nodes)

        query_values = {}
        for query in case["query_points"]:
            qx = _to_exact(query["x"])
            qy = _to_exact(query["y"])
            query_values[query["point_id"]] = [
                _to_fraction_string(shape_function.subs({x: qx, y: qy}))
                for shape_function in shape_functions
            ]

        result["cases"][case["case_id"]] = {
            "area": _to_fraction_string(area),
            "shape_functions": [str(shape_function) for shape_function in shape_functions],
            "gradient_matrix": gradient_matrix,
            "query_values": query_values,
        }

    return result


if __name__ == "__main__":
    output = derive_triangle_shape_data("/root/triangle_cases/triangle_cases.toml")
    print(json.dumps(output, indent=2))
EOF
