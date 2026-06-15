from decimal import Decimal
from datetime import date, datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse

from groups.models import Group, GroupMembership
from .models import ImportReport, ImportReportRow
from .services.parser import CSVParser
from .services.detector import AnomalyDetector
from .services.handler import ImportHandler

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


def is_active_member(group, user):
    return GroupMembership.objects.filter(
        group=group,
        user=user,
        left_at__isnull=True
    ).exists()


def make_serializable(data):
    if isinstance(data, dict):
        return {k: make_serializable(v) for k, v in data.items()}
    if isinstance(data, list):
        return [make_serializable(i) for i in data]
    if isinstance(data, Decimal):
        return str(data)
    if isinstance(data, (date, datetime)):
        return data.isoformat()
    return data



def build_imported_section(imported, styles):
    elements = []

    elements.append(Paragraph("✅ Imported / Converted", styles["Heading2"]))
    elements.append(Spacer(1, 8))

    data = [["Row", "Description", "Amount", "Action", "Note"]]

    for row in imported:
        data.append([
            str(row.row_number),
            (row.raw_data.get("description", "")[:40]),
            str(row.raw_data.get("amount", "")),
            row.action,
            (row.note or "")[:50]
        ])

    table = Table(data, colWidths=[40, 160, 70, 80, 150])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.green),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgreen]),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 20))
    return elements


def build_skipped_section(skipped, styles):
    elements = []

    elements.append(Paragraph("❌ Skipped", styles["Heading2"]))
    elements.append(Spacer(1, 8))

    data = [["Row", "Description", "Amount", "Reason"]]

    for row in skipped:
        data.append([
            str(row.row_number),
            (row.raw_data.get("description", "")[:40]),
            str(row.raw_data.get("amount", "")),
            (row.note or "")[:60]
        ])

    table = Table(data, colWidths=[40, 160, 70, 230])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.red),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.mistyrose]),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))

    elements.append(table)
    return elements



@login_required
def download_report_pdf(request, pk):
    report = get_object_or_404(ImportReport, id=pk, uploaded_by=request.user)
    rows = report.rows.all()

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="import_report_{report.id}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph(f"Import Report — {report.file_name}", styles["Title"]))
    elements.append(Spacer(1, 12))

    # Summary
    summary_data = [
        ["Total Rows", "Imported", "Skipped", "Status"],
        [str(report.total_rows), str(report.imported_rows), str(report.skipped_rows), report.status]
    ]

    summary_table = Table(summary_data, hAlign="LEFT")
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 1), (-1, -1), colors.lightblue),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
    ]))

    elements.append(summary_table)
    elements.append(Spacer(1, 20))

    # Sections
    imported = rows.filter(action__in=["IMPORTED", "CONVERTED"])
    skipped = rows.filter(action="SKIPPED")

    if imported.exists():
        elements += build_imported_section(imported, styles)

    if skipped.exists():
        elements += build_skipped_section(skipped, styles)

    doc.build(elements)
    return response



@login_required
@require_http_methods(["GET", "POST"])
def import_csv(request):
    groups = Group.objects.filter(
        memberships__user=request.user,
        memberships__left_at__isnull=True
    )

    if request.method == "GET":
        return render(request, "importer/upload.html", {"groups": groups})

    group = get_object_or_404(Group, id=request.POST.get("group_id"))

    if not is_active_member(group, request.user):
        messages.error(request, "You are not a member of this group")
        return redirect("importer:import_csv")

    csv_file = request.FILES.get("csv_file")

    if not csv_file or not csv_file.name.endswith(".csv"):
        messages.error(request, "Please upload a valid CSV file")
        return redirect("importer:import_csv")

    try:
        with transaction.atomic():
            rows = CSVParser().parse(csv_file)
            rows = AnomalyDetector().detect(rows)

            report = ImportReport.objects.create(
                uploaded_by=request.user,
                file_name=csv_file.name,
                total_rows=len(rows),
                status="PENDING"
            )

            handler = ImportHandler(group=group, imported_by=request.user)
            results = handler.handle(rows)

            imported = 0
            skipped = 0

            for result in results:
                action = result.get("action")

                if action in ["IMPORTED", "CONVERTED"]:
                    imported += 1
                else:
                    skipped += 1

                ImportReportRow.objects.create(
                    report=report,
                    row_number=result.get("row_number"),
                    raw_data=make_serializable(result.get("raw_data")),
                    action=action,
                    anomalies=result.get("anomalies", []),
                    note=result.get("note", "")
                )

            report.imported_rows = imported
            report.skipped_rows = skipped
            report.status = "COMPLETED"
            report.save()

            messages.success(
                request,
                f"Import complete! {imported} imported, {skipped} skipped."
            )

            return redirect("importer:import_report", pk=report.id)

    except Exception as e:
        messages.error(request, f"Import failed: {str(e)}")
        return redirect("importer:import_csv")

@login_required
def import_report(request, pk):
    report = get_object_or_404(ImportReport, id=pk, uploaded_by=request.user)
    rows = report.rows.all()

    return render(request, "importer/report.html", {
        "report": report,
        "imported": rows.filter(action__in=["IMPORTED", "CONVERTED"]),
        "skipped": rows.filter(action="SKIPPED"),
        "flagged": rows.filter(action="FLAGGED"),
    })