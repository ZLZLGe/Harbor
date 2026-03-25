#!/usr/bin/env python3

from pathlib import Path
import shutil

from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas


def draw_page(pdf: canvas.Canvas, title: str, lines: list[str], source_tag: str) -> None:
    width, height = pdf._pagesize
    top = height - 72

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(54, top, title)

    pdf.setFont("Helvetica", 12)
    y = top - 36
    for line in lines:
        pdf.drawString(54, y, line)
        y -= 20

    pdf.setFont("Helvetica-Oblique", 10)
    pdf.drawString(54, 36, source_tag)
    pdf.drawRightString(width - 54, 36, "Site packet source page")


def make_gate_briefing(path: Path) -> None:
    pdf = canvas.Canvas(str(path), pagesize=letter)
    draw_page(
        pdf,
        "Packet Section: Gate Briefing",
        [
            "Badge pickup window: 05:45-06:15",
            "North gate only before first horn.",
            "Escort contractor vans through checkpoint B.",
        ],
        "Source: gate_briefing.pdf page 1",
    )
    pdf.showPage()
    draw_page(
        pdf,
        "Packet Section: Break Rotation",
        [
            "Coffee trailer opens after scaffold inspection.",
            "This page is not part of the final packet.",
        ],
        "Source: gate_briefing.pdf page 2",
    )
    pdf.save()


def make_crew_packets(path: Path) -> None:
    pdf = canvas.Canvas(str(path), pagesize=landscape(letter))
    draw_page(
        pdf,
        "Packet Section: Emergency Contacts",
        [
            "Foam trailer dispatch: Channel 4",
            "Medic van standby at lot C.",
            "Notify fire watch before any hot restart.",
        ],
        "Source: crew_packets.pdf page 1",
    )
    pdf.showPage()
    pdf.setPageSize(letter)
    draw_page(
        pdf,
        "Packet Section: Crew Roster",
        [
            "Lift Team Bravo",
            "Pipefit crew starts at bay 7.",
            "Signal lead signs in with the crane desk.",
        ],
        "Source: crew_packets.pdf page 2",
    )
    pdf.save()


def make_crane_path_sheet(path: Path) -> None:
    pdf = canvas.Canvas(str(path), pagesize=landscape(letter))
    draw_page(
        pdf,
        "Packet Section: Crane Path Diagram",
        [
            "Keep southern lane clear.",
            "Swing radius crosses scaffold grid D.",
            "Spotter station remains at marker 12.",
        ],
        "Source: crane_path_sheet.pdf page 1",
    )
    pdf.save()


def make_permit_stack(path: Path) -> None:
    pdf = canvas.Canvas(str(path), pagesize=letter)
    draw_page(
        pdf,
        "Packet Section: Permit Summary",
        [
            "Night pour authorization",
            "Inspection hold lifted at 19:10.",
            "Concrete washout crew assigned to drain east.",
        ],
        "Source: permit_stack.pdf page 1",
    )
    pdf.showPage()
    draw_page(
        pdf,
        "Packet Section: Waste Transfer",
        [
            "Barrel count updated at gate scale.",
            "This page is not part of the final packet.",
        ],
        "Source: permit_stack.pdf page 2",
    )
    pdf.showPage()
    draw_page(
        pdf,
        "Packet Section: Chemical Hold Points",
        [
            "Stop-work trigger: vapor alarm",
            "Hold point 2 requires gas check.",
            "Escalate to the controls trailer if readings drift.",
        ],
        "Source: permit_stack.pdf page 3",
    )
    pdf.save()


def main(input_dir: str, output_dir: str) -> None:
    src = Path(input_dir)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    make_gate_briefing(out / "gate_briefing.pdf")
    make_crew_packets(out / "crew_packets.pdf")
    make_crane_path_sheet(out / "crane_path_sheet.pdf")
    make_permit_stack(out / "permit_stack.pdf")
    shutil.copy2(src / "assembly_order.txt", out / "assembly_order.txt")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        raise SystemExit("usage: create_site_packet_assets.py <input_dir> <output_dir>")
    main(sys.argv[1], sys.argv[2])
