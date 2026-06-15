from django.urls import path
from . import views

app_name = "importer"

urlpatterns = [
    path("", views.import_csv, name="import_csv"),
    path("report/<int:pk>/", views.import_report, name="import_report"),
    # path("report/<int:pk>/download/", views.download_report, name="download_report"),
    path("report/<int:pk>/download/pdf/", views.download_report_pdf, name="download_report_pdf"),
]