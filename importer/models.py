from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class ImportReport(models.Model):

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
    ]

    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="import_reports"
    )

    file_name = models.CharField(max_length=255)
    total_rows = models.IntegerField(default=0)
    imported_rows = models.IntegerField(default=0)
    skipped_rows = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Import {self.file_name} by {self.uploaded_by}"


class ImportReportRow(models.Model):

    ACTION_CHOICES = [
        ("IMPORTED", "Imported"),
        ("SKIPPED", "Skipped"),
        ("CONVERTED", "Converted"),
        ("FLAGGED", "Flagged"),
    ]

    report = models.ForeignKey(
        ImportReport,
        on_delete=models.CASCADE,
        related_name="rows"
    )

    row_number = models.IntegerField()
    raw_data = models.JSONField()
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    anomalies = models.JSONField(default=list)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["row_number"]

    def __str__(self):
        return f"Row {self.row_number} — {self.action}"