from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


OUTPUT_PATH = "/root/hearing_materials_mixed_source"

PAGES = [
    {
        "case_id": "HB-24-088",
        "exhibit_id": "EX-02",
        "exhibit_page": 1,
        "exhibit_total": 2,
        "title": "Resident Parking Survey Summary",
        "lines": [
            "Survey batch RPS-14 counted curb occupancy near Pier Avenue on June 3.",
            "Peak occupancy reached 87 percent between 6:15 PM and 7:00 PM.",
            "Witness note: overflow vehicles were redirected to Harbor Lot C.",
            "Prepared for the zoning variance hearing clerk file.",
        ],
    },
    {
        "case_id": "HB-24-071",
        "exhibit_id": "EX-05",
        "exhibit_page": 1,
        "exhibit_total": 4,
        "title": "Email Chain About Loading Berth Access",
        "lines": [
            "Message 1 of 4 records the contractor request for after-hours gate access.",
            "Sender: Dana Morrow, Operations Superintendent.",
            "Quoted request window: July 11 from 8:30 PM to 11:00 PM.",
            "Attachment reference: berth-layout-draft-A.pdf.",
        ],
    },
    {
        "case_id": "HB-24-071",
        "exhibit_id": "EX-02",
        "exhibit_page": 1,
        "exhibit_total": 3,
        "title": "Photo Log For North Loading Dock",
        "lines": [
            "Image set page 1 captures the north facade before temporary barriers were moved.",
            "Visible marker card reads Dock-N-01 beside the steel roll-up door.",
            "Clerk note confirms the photograph date as July 8 at 7:42 AM.",
            "Lighting conditions were overcast with no precipitation.",
        ],
    },
    {
        "case_id": "HB-24-071",
        "exhibit_id": "EX-05",
        "exhibit_page": 2,
        "exhibit_total": 4,
        "title": "Email Chain About Loading Berth Access",
        "lines": [
            "Message 2 of 4 states the fire lane must remain clear during all deliveries.",
            "Sender: Mira Chen, Deputy Fire Marshal.",
            "The reply rejects any trailer staging within 20 feet of hydrant H-3.",
            "Follow-up requested a revised circulation sketch by 4:00 PM.",
        ],
    },
    {
        "case_id": "HB-24-071",
        "exhibit_id": "EX-09",
        "exhibit_page": 1,
        "exhibit_total": 2,
        "title": "Inspector Memorandum On Traffic Queueing",
        "lines": [
            "Memorandum page 1 summarizes six observed truck queue events at the alley apron.",
            "Longest queue measured 118 feet beyond the painted stop line.",
            "Inspector Lara Singh recommends a staffed flagger during peak unloading windows.",
            "Reference photo index: TQ-071-A through TQ-071-F.",
        ],
    },
    {
        "case_id": "HB-24-088",
        "exhibit_id": "EX-11",
        "exhibit_page": 1,
        "exhibit_total": 2,
        "title": "Noise Meter Calibration Sheet",
        "lines": [
            "Calibration run CM-88-A shows baseline at 42.1 dBA.",
            "Instrument serial number is NM-4471 with annual service current.",
            "Field technician initials: JP.",
            "Sheet entered into the annex variance hearing binder.",
        ],
    },
    {
        "case_id": "HB-24-071",
        "exhibit_id": "EX-02",
        "exhibit_page": 2,
        "exhibit_total": 3,
        "title": "Photo Log For North Loading Dock",
        "lines": [
            "Image set page 2 shows the temporary jersey barrier aligned with stripe bay B.",
            "Marker card Dock-N-02 is visible beside the forklift charging station.",
            "Measured clearance between barrier edge and curb return is 11 feet 4 inches.",
            "A safety cone blocks the eastern pedestrian crossover.",
        ],
    },
    {
        "case_id": "HB-24-071",
        "exhibit_id": "EX-05",
        "exhibit_page": 3,
        "exhibit_total": 4,
        "title": "Email Chain About Loading Berth Access",
        "lines": [
            "Message 3 of 4 proposes moving the temporary fence panel by one vehicle length.",
            "Sender: Omar Velasquez, project civil engineer.",
            "The sketch note identifies turning path template WB-40 as acceptable.",
            "Final review was scheduled for the July 12 coordination call.",
        ],
    },
    {
        "case_id": "HB-24-088",
        "exhibit_id": "EX-02",
        "exhibit_page": 2,
        "exhibit_total": 2,
        "title": "Resident Parking Survey Summary",
        "lines": [
            "Survey batch RPS-14 page 2 lists resident comments from the east block.",
            "Thirty-one comments opposed extending loading hours past 9:00 PM.",
            "Seven comments supported valet overflow management.",
            "Clerk routing stamp indicates annex packet section four.",
        ],
    },
    {
        "case_id": "HB-24-071",
        "exhibit_id": "EX-09",
        "exhibit_page": 2,
        "exhibit_total": 2,
        "title": "Inspector Memorandum On Traffic Queueing",
        "lines": [
            "Memorandum page 2 lists corrective actions and a two-week follow-up timeline.",
            "Recommended curb marshal hours are 6:30 AM to 9:30 AM on weekdays.",
            "The note states no queueing was observed after temporary signage was installed.",
            "Prepared for record submission by Inspector Lara Singh.",
        ],
    },
    {
        "case_id": "HB-24-071",
        "exhibit_id": "EX-05",
        "exhibit_page": 4,
        "exhibit_total": 4,
        "title": "Email Chain About Loading Berth Access",
        "lines": [
            "Message 4 of 4 confirms the revised plan may proceed subject to hydrant clearance.",
            "Sender: Board Clerk Elena Park.",
            "The approval note references hearing calendar slot HB-24-071-3C.",
            "Distribution list includes planning, fire prevention, and operations teams.",
        ],
    },
    {
        "case_id": "HB-24-071",
        "exhibit_id": "EX-02",
        "exhibit_page": 3,
        "exhibit_total": 3,
        "title": "Photo Log For North Loading Dock",
        "lines": [
            "Image set page 3 documents the reopened pedestrian route after barrier removal.",
            "Marker card Dock-N-03 is positioned next to the bollard row.",
            "The painted curb legend remains fully visible from the west approach.",
            "No obstructions remain in the striped crossing at capture time.",
        ],
    },
    {
        "case_id": "HB-24-088",
        "exhibit_id": "EX-11",
        "exhibit_page": 2,
        "exhibit_total": 2,
        "title": "Noise Meter Calibration Sheet",
        "lines": [
            "Calibration run CM-88-B verifies field tolerance remained within 0.2 dBA.",
            "Post-run check time was logged at 8:17 PM.",
            "Technician JP certified the unit before the evening measurement session.",
            "Annex packet cross-reference: acoustics supplement page 5.",
        ],
    },
]


def draw_page(pdf: canvas.Canvas, record: dict) -> None:
    width, height = letter
    left = 54
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(left, height - 54, "North Harbor Zoning Board Hearing Record")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(
        left,
        height - 72,
        f"Case: {record['case_id']}   Exhibit: {record['exhibit_id']}   "
        f"Exhibit Page: {record['exhibit_page']} of {record['exhibit_total']}",
    )
    pdf.line(left, height - 82, width - left, height - 82)

    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(left, height - 118, record["title"])

    pdf.setFont("Helvetica", 11)
    y = height - 150
    for line in record["lines"]:
        pdf.drawString(left, y, line)
        y -= 18

    pdf.line(left, 74, width - left, 74)
    pdf.setFont("Helvetica-Oblique", 9)
    pdf.drawString(
        left,
        58,
        f"Clerk Index: {record['case_id']} / {record['exhibit_id']} / Sheet {record['exhibit_page']}",
    )
    pdf.drawRightString(width - left, 58, "Mixed Hearing Binder 2026")
    pdf.showPage()


def main() -> None:
    pdf = canvas.Canvas(OUTPUT_PATH, pagesize=letter)
    pdf.setTitle("Mixed Hearing Materials")
    pdf.setAuthor("Harbor Task Builder")

    for record in PAGES:
        draw_page(pdf, record)

    pdf.save()


if __name__ == "__main__":
    main()
