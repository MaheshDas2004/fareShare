from django.urls import path
from . import views

app_name = "settlements"

urlpatterns = [
    path("create/", views.create_settlement, name="create_settlement"),
    path("<int:pk>/delete/", views.delete_settlement, name="delete_settlement"),
]