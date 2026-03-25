#!/bin/bash
set -euo pipefail

mkdir -p /root/output

python3 <<'PY'
import json
import subprocess
from math import ceil
from pathlib import Path

from openpyxl import load_workbook

INPUT_PATH = Path("/root/data/restock_planner.xlsx")
OUTPUT_PATH = Path("/root/output/restock_dispatch_board.xlsx")

wb = load_workbook(INPUT_PATH)
demand_ws = wb["Demand"]
on_hand_ws = wb["On Hand"]
inbound_ws = wb["Inbound"]
lead_ws = wb["Lead Times"]
case_ws = wb["Case Packs"]
plan_ws = wb["Restock Plan"]
board_ws = wb["Dispatch Board"]


def populated_rows(ws, key_col=1):
    rows = []
    for row in range(2, ws.max_row + 1):
        value = ws.cell(row=row, column=key_col).value
        if value in (None, ""):
            continue
        rows.append(row)
    return rows


demand_rows = populated_rows(demand_ws)
on_hand_end = max(populated_rows(on_hand_ws))
inbound_end = max(populated_rows(inbound_ws))
lead_end = max(populated_rows(lead_ws))
case_end = max(populated_rows(case_ws))

for out_row, demand_row in enumerate(demand_rows, start=2):
    plan_ws[f"A{out_row}"] = f"=Demand!A{demand_row}"
    plan_ws[f"B{out_row}"] = f"=Demand!B{demand_row}"
    plan_ws[f"C{out_row}"] = f"=Demand!C{demand_row}"
    plan_ws[f"D{out_row}"] = f"=Demand!D{demand_row}"
    plan_ws[f"E{out_row}"] = (
        f"=SUMIFS('On Hand'!$C$2:$C${on_hand_end},'On Hand'!$A$2:$A${on_hand_end},A{out_row},"
        f"'On Hand'!$B$2:$B${on_hand_end},B{out_row})"
    )
    plan_ws[f"F{out_row}"] = (
        f"=INDEX('Lead Times'!$B$2:$B${lead_end},MATCH(A{out_row},'Lead Times'!$A$2:$A${lead_end},0))"
    )
    plan_ws[f"G{out_row}"] = (
        f"=SUMIFS(Inbound!$D$2:$D${inbound_end},Inbound!$A$2:$A${inbound_end},A{out_row},"
        f"Inbound!$B$2:$B${inbound_end},B{out_row},Inbound!$C$2:$C${inbound_end},\"<=\"&F{out_row})"
    )
    plan_ws[f"H{out_row}"] = (
        f"=SUMIFS(Inbound!$D$2:$D${inbound_end},Inbound!$A$2:$A${inbound_end},A{out_row},"
        f"Inbound!$B$2:$B${inbound_end},B{out_row})"
    )
    plan_ws[f"I{out_row}"] = f"=MAX(C{out_row}*F{out_row}-E{out_row}-G{out_row},0)"
    plan_ws[f"J{out_row}"] = f"=MAX(C{out_row}*(D{out_row}+F{out_row})-E{out_row}-H{out_row},0)"
    plan_ws[f"K{out_row}"] = (
        f"=INDEX('Case Packs'!$B$2:$B${case_end},MATCH(B{out_row},'Case Packs'!$A$2:$A${case_end},0))"
    )
    plan_ws[f"L{out_row}"] = f"=IF(J{out_row}=0,0,CEILING(J{out_row},K{out_row}))"
    plan_ws[f"M{out_row}"] = f"=(E{out_row}+H{out_row}+L{out_row})/C{out_row}-F{out_row}"
    plan_ws[f"N{out_row}"] = f"=I{out_row}*100+MAX(D{out_row}-M{out_row},0)"
    plan_ws[f"O{out_row}"] = (
        f"=IF(I{out_row}>=C{out_row}*2,\"CRITICAL\",IF(I{out_row}>0,\"WATCH\",\"OK\"))"
    )

    plan_ws[f"C{out_row}"].number_format = "0.00"
    plan_ws[f"D{out_row}"].number_format = "0"
    for col in ["E", "F", "G", "H", "I", "J", "K", "L", "N"]:
        plan_ws[f"{col}{out_row}"].number_format = "0"
    plan_ws[f"M{out_row}"].number_format = "0.00"

# Clear any remaining rows within the template window.
for row in range(len(demand_rows) + 2, 12):
    for col in range(1, 16):
        plan_ws.cell(row=row, column=col).value = None
    for col in range(1, 9):
        board_ws.cell(row=row, column=col).value = None

on_hand = {}
for row in populated_rows(on_hand_ws):
    key = (on_hand_ws[f"A{row}"].value, on_hand_ws[f"B{row}"].value)
    on_hand[key] = float(on_hand_ws[f"C{row}"].value)

lead_times = {}
for row in populated_rows(lead_ws):
    lead_times[lead_ws[f"A{row}"].value] = float(lead_ws[f"B{row}"].value)

case_packs = {}
for row in populated_rows(case_ws):
    case_packs[case_ws[f"A{row}"].value] = float(case_ws[f"B{row}"].value)

inbound = {}
for row in populated_rows(inbound_ws):
    key = (inbound_ws[f"A{row}"].value, inbound_ws[f"B{row}"].value)
    inbound.setdefault(key, []).append(
        (float(inbound_ws[f"C{row}"].value), float(inbound_ws[f"D{row}"].value))
    )

ranked = []
for plan_row, demand_row in enumerate(demand_rows, start=2):
    store = demand_ws[f"A{demand_row}"].value
    sku = demand_ws[f"B{demand_row}"].value
    demand = float(demand_ws[f"C{demand_row}"].value)
    target_cover = float(demand_ws[f"D{demand_row}"].value)
    lead_days = lead_times[store]
    inbound_lines = inbound.get((store, sku), [])
    inbound_before = sum(qty for eta, qty in inbound_lines if eta <= lead_days)
    inbound_total = sum(qty for _, qty in inbound_lines)
    gap = max(demand * lead_days - on_hand[(store, sku)] - inbound_before, 0)
    net_need = max(demand * (target_cover + lead_days) - on_hand[(store, sku)] - inbound_total, 0)
    case_pack = case_packs[sku]
    suggested = 0 if net_need == 0 else ceil(net_need / case_pack) * case_pack
    cover = (on_hand[(store, sku)] + inbound_total + suggested) / demand - lead_days
    urgency = gap * 100 + max(target_cover - cover, 0)
    ranked.append(
        {
            "plan_row": plan_row,
            "store": store,
            "sku": sku,
            "gap": gap,
            "urgency": urgency,
        }
    )

ranked.sort(key=lambda item: (-item["urgency"], -item["gap"], item["store"], item["sku"]))

for rank, item in enumerate(ranked, start=1):
    row = rank + 1
    source_row = item["plan_row"]
    board_ws[f"A{row}"] = rank
    board_ws[f"B{row}"] = f"='Restock Plan'!A{source_row}"
    board_ws[f"C{row}"] = f"='Restock Plan'!B{source_row}"
    board_ws[f"D{row}"] = f"='Restock Plan'!I{source_row}"
    board_ws[f"E{row}"] = f"='Restock Plan'!L{source_row}"
    board_ws[f"F{row}"] = f"='Restock Plan'!M{source_row}"
    board_ws[f"G{row}"] = f"='Restock Plan'!O{source_row}"
    board_ws[f"H{row}"] = f"='Restock Plan'!N{source_row}"
    board_ws[f"D{row}"].number_format = "0"
    board_ws[f"E{row}"].number_format = "0"
    board_ws[f"F{row}"].number_format = "0.00"
    board_ws[f"H{row}"].number_format = "0.00"

wb.save(OUTPUT_PATH)

result = subprocess.run(
    ["python3", "/root/.codex/skills/xlsx/recalc.py", str(OUTPUT_PATH), "60"],
    check=True,
    capture_output=True,
    text=True,
)
payload = json.loads(result.stdout)
if payload.get("status") != "success":
    raise SystemExit(result.stdout)
PY
