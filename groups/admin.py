from django.contrib import admin
from .models import Group, GroupMembership


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_by", "default_currency", "is_archived", "created_at")
    search_fields = ("name",)
    list_filter = ("is_archived", "default_currency")


@admin.register(GroupMembership)
class GroupMembershipAdmin(admin.ModelAdmin):
    list_display = ("id", "group", "user", "is_active", "joined_at")
    search_fields = ("group__name", "user__username")
    list_filter = ("is_active",)