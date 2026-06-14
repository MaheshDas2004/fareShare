from django.urls import path

from .views import add_member, create_group, group_detail, group_list, leave_group

app_name = "groups"

urlpatterns = [
    path("", group_list, name="group_list"),
    path("create/", create_group, name="create_group"),
    path("<int:pk>/", group_detail, name="group_detail"),
    path("<int:pk>/add-member/", add_member, name="add_member"),
    path("<int:pk>/leave/", leave_group, name="leave_group"),
]