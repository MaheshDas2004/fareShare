from django.urls import path
from . import views

urlpatterns = [
    path("create/", views.create_settlement, name="create_settlement"),
    path("delete/<int:pk>/", views.delete_settlement, name="delete_settlement"),
]