from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.db import transaction
from decimal import Decimal
from datetime import date, datetime

from groups.models import Group, GroupMembership
from .models import ImportReport, ImportReportRow
from .services.parser import CSVParser
from .services.detector import AnomalyDetector
from .services.handler import ImportHandler


def is_active_member(group, user):
    return GroupMembership.objects.filter(
        group=group,
        user=user,
        left_at__isnull=True
    ).exists()


def make_serializable(data):
    if isinstance(data, dict):
        return {k: make_serializable(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [make_serializable(i) for i in data]
    elif isinstance(data, Decimal):
        return str(data)
    elif isinstance(data, (date, datetime)):
        return data.isoformat()
    return data


@login_required
@require_http_methods(["GET", "POST"])
def import_csv(request):
    groups = Group.objects.filter(
        memberships__user=request.user,
        memberships__left_at__isnull=True
    )

    if request.method == "GET":
        return render(request, "importer/upload.html", {
            "groups": groups
        })

    group = get_object_or_404(Group, id=request.POST.get("group_id"))

    if not is_active_member(group, request.user):
        messages.error(request, "You are not a member of this group")
        return redirect("importer:import_csv")

    csv_file = request.FILES.get("csv_file")

    if not csv_file:
        messages.error(request, "Please upload a CSV file")
        return redirect("importer:import_csv")

    if not csv_file.name.endswith(".csv"):
        messages.error(request, "Only CSV files are allowed")
        return redirect("importer:import_csv")

    try:
        with transaction.atomic():
            parser = CSVParser()
            rows = parser.parse(csv_file)

            detector = AnomalyDetector()
            rows = detector.detect(rows)

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

            messages.success(request, f"Import complete! {imported} imported, {skipped} skipped.")
            return redirect("importer:import_report", pk=report.id)

    except Exception as e:
        messages.error(request, f"Import failed: {str(e)}")
        return redirect("importer:import_csv")


@login_required
def import_report(request, pk):
    report = get_object_or_404(ImportReport, id=pk, uploaded_by=request.user)
    rows = report.rows.all()

    imported = rows.filter(action__in=["IMPORTED", "CONVERTED"])
    skipped = rows.filter(action="SKIPPED")
    flagged = rows.filter(action="FLAGGED")

    return render(request, "importer/report.html", {
        "report": report,
        "imported": imported,
        "skipped": skipped,
        "flagged": flagged
    })