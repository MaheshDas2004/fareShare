from django.contrib import admin
from .models import Group, GroupMembership


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_by", "default_currency", "is_archived", "created_at")
    search_fields = ("name",)
    list_filter = ("is_archived",)


@admin.register(GroupMembership)
class GroupMembershipAdmin(admin.ModelAdmin):
    list_display = ("id", "group", "user", "is_active", "joined_at", "left_at")
    search_fields = ("group__name", "user__username")
    list_filter = ("left_at",)