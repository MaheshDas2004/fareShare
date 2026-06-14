from django.urls import path
from . import views

urlpatterns = [
    path("create/", views.create_expense, name="create_expense"),
    path("delete/<int:pk>/", views.delete_expense, name="delete_expense"),
    path("group/<int:group_id>/balances/", views.group_balances, name="group_balances"),
    path("my-balances/", views.user_balances, name="user_balances"),
]