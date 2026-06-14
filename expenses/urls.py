from django.urls import path
from . import views

app_name = "expenses"

urlpatterns = [
    path("create/", views.create_expense, name="create_expense"),
    path("<int:pk>/edit/", views.edit_expense, name="edit_expense"),
    path("<int:pk>/delete/", views.delete_expense, name="delete_expense"),
    path("<int:pk>/", views.expense_detail, name="expense_detail"),
    path("group/<int:group_id>/", views.expense_list, name="expense_list"),
    path("group/<int:group_id>/balances/", views.group_balances, name="group_balances"),
    path("my-balances/", views.user_balances, name="user_balances"),
]