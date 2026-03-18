#!/usr/bin/env python3

import csv
import os
from pathlib import Path


ARCHIVED_ROWS = [
    {
        "sku": "VND-1001",
        "product_name": "Acrylic Display Stand",
        "unit_price": "12.50",
        "min_order_qty": "20",
        "category": "display",
    },
    {
        "sku": "VND-1002",
        "product_name": "Brushed Steel Hook",
        "unit_price": "1.25",
        "min_order_qty": "200",
        "category": "hardware",
    },
    {
        "sku": "VND-1003",
        "product_name": "Countertop Sign Holder",
        "unit_price": "4.80",
        "min_order_qty": "60",
        "category": "display",
    },
    {
        "sku": "VND-1004",
        "product_name": "Floor Sticker Kit",
        "unit_price": "8.40",
        "min_order_qty": "40",
        "category": "promo",
    },
    {
        "sku": "VND-1005",
        "product_name": "Glass Shelf Clamp",
        "unit_price": "2.95",
        "min_order_qty": "100",
        "category": "hardware",
    },
    {
        "sku": "VND-1006",
        "product_name": "LED Shelf Strip 1m",
        "unit_price": "6.75",
        "min_order_qty": "30",
        "category": "lighting",
    },
    {
        "sku": "VND-1007",
        "product_name": "Matte Black Hanger",
        "unit_price": "2.10",
        "min_order_qty": "50",
        "category": "fixtures",
    },
    {
        "sku": "VND-1008",
        "product_name": "Pegboard Basket Small",
        "unit_price": "5.60",
        "min_order_qty": "25",
        "category": "fixtures",
    },
    {
        "sku": "VND-1009",
        "product_name": "Queue Barrier Rope",
        "unit_price": "18.00",
        "min_order_qty": "10",
        "category": "storefront",
    },
    {
        "sku": "VND-1010",
        "product_name": "Shelf Talker Clip",
        "unit_price": "0.55",
        "min_order_qty": "500",
        "category": "promo",
    },
    {
        "sku": "VND-1011",
        "product_name": "Slatwall Panel White",
        "unit_price": "27.50",
        "min_order_qty": "15",
        "category": "fixtures",
    },
    {
        "sku": "VND-1012",
        "product_name": "Wooden Risers Set",
        "unit_price": "14.20",
        "min_order_qty": "12",
        "category": "display",
    },
]

CURRENT_ROWS = [
    {
        "sku": "VND-1001",
        "product_name": "Acrylic Display Stand",
        "unit_price": "12.50",
        "min_order_qty": "20",
        "preferred_vendor": "North Pier Supply",
    },
    {
        "sku": "VND-1002",
        "product_name": "Brushed Steel Hook",
        "unit_price": "1.40",
        "min_order_qty": "200",
        "preferred_vendor": "North Pier Supply",
    },
    {
        "sku": "VND-1003",
        "product_name": "Countertop Sign Holder",
        "unit_price": "4.80",
        "min_order_qty": "60",
        "preferred_vendor": "North Pier Supply",
    },
    {
        "sku": "VND-1005",
        "product_name": "Glass Shelf Clamp",
        "unit_price": "2.95",
        "min_order_qty": "120",
        "preferred_vendor": "North Pier Supply",
    },
    {
        "sku": "VND-1006",
        "product_name": "LED Shelf Strip 1m",
        "unit_price": "6.75",
        "min_order_qty": "30",
        "preferred_vendor": "North Pier Supply",
    },
    {
        "sku": "VND-1007",
        "product_name": "Matte Black Hanger",
        "unit_price": "2.35",
        "min_order_qty": "40",
        "preferred_vendor": "North Pier Supply",
    },
    {
        "sku": "VND-1008",
        "product_name": "Pegboard Basket Small",
        "unit_price": "5.60",
        "min_order_qty": "25",
        "preferred_vendor": "North Pier Supply",
    },
    {
        "sku": "VND-1010",
        "product_name": "Shelf Talker Clip",
        "unit_price": "0.55",
        "min_order_qty": "500",
        "preferred_vendor": "North Pier Supply",
    },
    {
        "sku": "VND-1011",
        "product_name": "Slatwall Panel White",
        "unit_price": "29.00",
        "min_order_qty": "15",
        "preferred_vendor": "North Pier Supply",
    },
    {
        "sku": "VND-1012",
        "product_name": "Wooden Risers Set",
        "unit_price": "14.20",
        "min_order_qty": "12",
        "preferred_vendor": "North Pier Supply",
    },
    {
        "sku": "VND-1013",
        "product_name": "Wire Dump Bin",
        "unit_price": "31.00",
        "min_order_qty": "8",
        "preferred_vendor": "North Pier Supply",
    },
]


def pdf_escape(text):
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_simple_pdf(lines_by_page, destination):
    font_id = 1
    next_id = 2
    objects = {
        font_id: "<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>",
    }
    page_ids = []

    for page_lines in lines_by_page:
        content_id = next_id
        next_id += 1
        page_id = next_id
        next_id += 1
        page_ids.append(page_id)

        stream_ops = ["BT", "/F1 10 Tf", "12 TL", "54 756 Td"]
        for index, line in enumerate(page_lines):
            if index:
                stream_ops.append("T*")
            stream_ops.append(f"({pdf_escape(line)}) Tj")
        stream_ops.append("ET")
        stream = "\n".join(stream_ops)
        objects[content_id] = f"<< /Length {len(stream.encode('latin-1'))} >>\nstream\n{stream}\nendstream"
        objects[page_id] = (content_id, None)

    pages_id = next_id
    next_id += 1
    catalog_id = next_id

    for page_id in page_ids:
        content_id, _ = objects[page_id]
        objects[page_id] = (
            "<< /Type /Page /Parent "
            f"{pages_id} 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> "
            f"/Contents {content_id} 0 R >>"
        )

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[pages_id] = f"<< /Type /Pages /Count {len(page_ids)} /Kids [{kids}] >>"
    objects[catalog_id] = f"<< /Type /Catalog /Pages {pages_id} 0 R >>"

    pdf_parts = [b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"]
    offsets = [0]

    for object_id in range(1, catalog_id + 1):
        offsets.append(sum(len(part) for part in pdf_parts))
        obj = f"{object_id} 0 obj\n{objects[object_id]}\nendobj\n".encode("latin-1")
        pdf_parts.append(obj)

    xref_offset = sum(len(part) for part in pdf_parts)
    xref_lines = [f"xref\n0 {catalog_id + 1}\n", "0000000000 65535 f \n"]
    for offset in offsets[1:]:
        xref_lines.append(f"{offset:010d} 00000 n \n")
    pdf_parts.append("".join(xref_lines).encode("latin-1"))
    trailer = (
        f"trailer\n<< /Size {catalog_id + 1} /Root {catalog_id} 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    )
    pdf_parts.append(trailer.encode("latin-1"))
    destination.write_bytes(b"".join(pdf_parts))


def build_pdf_lines():
    per_page = 6
    header = [
        "Legacy Supplier Price List",
        "Supplier: Harbor Retail Fixtures",
        "Effective Date: 2025-01-15",
        "",
        "SKU | Product Name | Unit Price USD | Min Order Qty | Category",
        "----------------------------------------------------------------",
    ]

    pages = []
    total_pages = (len(ARCHIVED_ROWS) + per_page - 1) // per_page
    for page_index in range(total_pages):
        start = page_index * per_page
        end = start + per_page
        rows = ARCHIVED_ROWS[start:end]
        page_lines = list(header)
        page_lines.insert(3, f"Page {page_index + 1} of {total_pages}")
        for row in rows:
            page_lines.append(
                " | ".join(
                    [
                        row["sku"],
                        row["product_name"],
                        row["unit_price"],
                        row["min_order_qty"],
                        row["category"],
                    ]
                )
            )
        page_lines.extend(["", "Archived list kept for procurement audit only."])
        pages.append(page_lines)
    return pages


def write_csv(destination):
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "sku",
                "product_name",
                "unit_price",
                "min_order_qty",
                "preferred_vendor",
            ],
        )
        writer.writeheader()
        writer.writerows(CURRENT_ROWS)


def main():
    pdf_path = Path(os.environ.get("PDF_PATH", "/root/vendor_price_archive.pdf"))
    csv_path = Path(os.environ.get("CSV_PATH", "/root/current_procurement_list.csv"))

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    write_simple_pdf(build_pdf_lines(), pdf_path)
    write_csv(csv_path)


if __name__ == "__main__":
    main()
