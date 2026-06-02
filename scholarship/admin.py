from django.contrib import admin
from .models import (
    ScholarshipProgram, ApplicantProfile, EducationalBackground,
    ScholarshipApplication, KYCDocument, ApplicationActivityLog
)

@admin.register(ScholarshipProgram)
class ScholarshipProgramAdmin(admin.ModelAdmin):
    list_display = ['name', 'amount', 'deadline', 'is_active', 'created_at']
    list_filter = ['is_active', 'deadline']
    search_fields = ['name', 'description']
    date_hierarchy = 'deadline'

@admin.register(ApplicantProfile)
class ApplicantProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'city', 'region', 'country', 'created_at']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'national_id']
    list_filter = ['country', 'region', 'gender']

@admin.register(EducationalBackground)
class EducationalBackgroundAdmin(admin.ModelAdmin):
    list_display = ['applicant', 'institution_name', 'degree_type', 'field_of_study', 'start_date', 'end_date']
    list_filter = ['degree_type', 'country']
    search_fields = ['institution_name', 'field_of_study']

@admin.register(ScholarshipApplication)
class ScholarshipApplicationAdmin(admin.ModelAdmin):
    list_display = ['id', 'applicant', 'program', 'status', 'submitted_at', 'created_at']
    list_filter = ['status', 'program', 'created_at']
    search_fields = ['applicant__user__username', 'applicant__user__email', 'program__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'

@admin.register(KYCDocument)
class KYCDocumentAdmin(admin.ModelAdmin):
    list_display = ['document_type', 'application', 'verification_status', 'uploaded_at', 'verified_at']
    list_filter = ['document_type', 'verification_status', 'uploaded_at']
    search_fields = ['application__applicant__user__username', 'file_name']

@admin.register(ApplicationActivityLog)
class ApplicationActivityLogAdmin(admin.ModelAdmin):
    list_display = ['application', 'action', 'performed_by', 'timestamp']
    list_filter = ['action', 'timestamp']
    search_fields = ['application__id', 'description']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
