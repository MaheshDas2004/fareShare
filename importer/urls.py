from django.urls import path
from . import views

app_name = "importer"

urlpatterns = [
    path("", views.import_csv, name="import_csv"),
    path("report/<int:pk>/", views.import_report, name="import_report"),
]