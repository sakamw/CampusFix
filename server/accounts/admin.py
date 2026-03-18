from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, SupportRequest


class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['email', 'first_name', 'last_name', 'student_id', 'role', 'is_active']
    list_filter = ['role', 'is_active', 'is_staff']
    search_fields = ['email', 'first_name', 'last_name', 'student_id']
    ordering = ['email']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'student_id', 'phone', 'avatar')}),
        ('Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'student_id', 'password1', 'password2', 'role', 'is_active', 'is_staff'),
        }),
    )


@admin.register(SupportRequest)
class SupportRequestAdmin(admin.ModelAdmin):
    list_display = ['support_type', 'subject', 'user', 'is_resolved', 'created_at']
    list_filter = ['support_type', 'is_resolved', 'created_at']
    search_fields = ['subject', 'message', 'user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['user', 'support_type', 'subject', 'message', 'created_at', 'updated_at']
    ordering = ['-created_at']


admin.site.register(User, CustomUserAdmin)
