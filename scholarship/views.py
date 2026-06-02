from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseForbidden, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import (
    ScholarshipProgram, ApplicantProfile, EducationalBackground,
    ScholarshipApplication, KYCDocument, ApplicationActivityLog
)
from .forms import (
    HoneypotRegistrationForm, ApplicantProfileForm, EducationalBackgroundFormSet,
    ScholarshipApplicationForm, KYCDocumentForm, BulkActionForm,
    StatusUpdateForm, DocumentVerificationForm
)


def is_coordinator(user):
    """Check if user is a regional coordinator (staff or superuser)."""
    return user.is_staff or user.is_superuser


def log_activity(application, action, performed_by, description, old_value='', new_value='', ip_address=None):
    """Helper to create audit log entries."""
    ApplicationActivityLog.objects.create(
        application=application,
        action=action,
        performed_by=performed_by,
        description=description,
        old_value=old_value,
        new_value=new_value,
        ip_address=ip_address
    )


# ==============================================================================
# PUBLIC PAGES
# ==============================================================================

def home(request):
    """Public landing page showing available scholarship programs."""
    programs = ScholarshipProgram.objects.filter(is_active=True, deadline__gte=timezone.now().date())
    return render(request, 'scholarship/home.html', {'programs': programs})


def register(request):
    """Registration with honeypot anti-spam protection."""
    if request.method == 'POST':
        form = HoneypotRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create empty profile
            ApplicantProfile.objects.create(user=user)
            login(request, user)
            messages.success(request, 'Account created successfully! Please complete your profile.')
            return redirect('profile_setup')
    else:
        form = HoneypotRegistrationForm()
    return render(request, 'scholarship/register.html', {'form': form})


# ==============================================================================
# APPLICANT DASHBOARD (ANTI-IDOR: Users can ONLY see their own data)
# ==============================================================================

@login_required
def profile_setup(request):
    """Step 1: Complete applicant profile and educational background (formsets)."""
    profile, created = ApplicantProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        profile_form = ApplicantProfileForm(request.POST, instance=profile)
        formset = EducationalBackgroundFormSet(request.POST, instance=profile)
        
        if profile_form.is_valid() and formset.is_valid():
            profile_form.save()
            formset.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('dashboard')
    else:
        profile_form = ApplicantProfileForm(instance=profile)
        formset = EducationalBackgroundFormSet(instance=profile)
    
    return render(request, 'scholarship/profile_setup.html', {
        'profile_form': profile_form,
        'formset': formset,
    })


@login_required
def dashboard(request):
    """Applicant dashboard - shows only THEIR applications (Anti-IDOR)."""
    # Auto-create profile if it doesn't exist (e.g., superuser created via CLI)
    profile, created = ApplicantProfile.objects.get_or_create(user=request.user)
    
    # Anti-IDOR: Scope ALL queries to the current user
    applications = ScholarshipApplication.objects.filter(applicant=profile).select_related('program')
    documents = KYCDocument.objects.filter(application__applicant=profile)
    
    return render(request, 'scholarship/dashboard.html', {
        'applications': applications,
        'documents': documents,
        'profile': profile,
    })


@login_required
def apply_scholarship(request):
    """Create a new scholarship application."""
    profile, created = ApplicantProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = ScholarshipApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.applicant = profile
            application.save()
            log_activity(application, 'created', request.user, 'Application created')
            messages.success(request, 'Application started! Please upload your KYC documents.')
            return redirect('application_detail', pk=application.pk)
    else:
        form = ScholarshipApplicationForm()
    
    return render(request, 'scholarship/apply.html', {'form': form})


@login_required
def application_detail(request, pk):
    """
    Anti-IDOR: Students can ONLY view their own applications.
    Uses UUID pk and scoped queryset to prevent enumeration attacks.
    """
    profile, created = ApplicantProfile.objects.get_or_create(user=request.user)
    
    # Anti-IDOR: Filter by applicant in the query - returns 404 if not theirs
    application = get_object_or_404(
        ScholarshipApplication.objects.select_related('program'),
        pk=pk,
        applicant=profile  # <-- CRITICAL: scopes to requesting user
    )
    
    documents = KYCDocument.objects.filter(application=application)
    activity_logs = application.activity_logs.select_related('performed_by')[:20]
    
    if request.method == 'POST' and application.status == 'draft':
        doc_form = KYCDocumentForm(request.POST, request.FILES)
        if doc_form.is_valid():
            doc = doc_form.save(commit=False)
            doc.application = application
            doc.file_name = request.FILES['file'].name
            doc.save()
            log_activity(application, 'document_uploaded', request.user, f'Document uploaded: {doc.get_document_type_display()}')
            messages.success(request, 'Document uploaded successfully!')
            return redirect('application_detail', pk=application.pk)
    else:
        doc_form = KYCDocumentForm()
    
    return render(request, 'scholarship/application_detail.html', {
        'application': application,
        'documents': documents,
        'doc_form': doc_form,
        'activity_logs': activity_logs,
        'can_submit': application.status == 'draft' and documents.exists(),
    })


@login_required
@require_POST
def submit_application(request, pk):
    """Submit a draft application for review."""
    profile, created = ApplicantProfile.objects.get_or_create(user=request.user)
    application = get_object_or_404(ScholarshipApplication, pk=pk, applicant=profile)
    
    if application.status != 'draft':
        messages.error(request, 'This application has already been submitted.')
        return redirect('application_detail', pk=pk)
    
    # Check required documents exist
    if not application.documents.exists():
        messages.error(request, 'Please upload at least one KYC document before submitting.')
        return redirect('application_detail', pk=pk)
    
    application.status = 'submitted'
    application.submitted_at = timezone.now()
    application.save()
    log_activity(application, 'submitted', request.user, 'Application submitted for review')
    messages.success(request, 'Application submitted successfully! You will be notified of updates.')
    return redirect('dashboard')


@login_required
def delete_document(request, doc_id):
    """Anti-IDOR: Only allow deleting own documents."""
    profile, created = ApplicantProfile.objects.get_or_create(user=request.user)
    document = get_object_or_404(KYCDocument, pk=doc_id, application__applicant=profile)
    application = document.application
    
    if request.method == 'POST':
        document.delete()
        log_activity(application, 'updated', request.user, f'Document deleted: {document.get_document_type_display()}')
        messages.success(request, 'Document deleted.')
        return redirect('application_detail', pk=application.pk)
    
    return render(request, 'scholarship/confirm_delete.html', {
        'object': document,
        'title': 'Delete Document',
        'message': f'Are you sure you want to delete "{document.get_document_type_display()}"?'
    })


# ==============================================================================
# COORDINATOR DASHBOARD (Backend for regional coordinators)
# ==============================================================================

@login_required
@user_passes_test(is_coordinator)
def coordinator_dashboard(request):
    """Coordinator dashboard with filtering, search, and bulk actions."""
    # Base queryset with related data for performance
    applications = ScholarshipApplication.objects.select_related(
        'applicant__user', 'program', 'reviewed_by'
    ).prefetch_related('documents')
    
    # -- Filters --
    status_filter = request.GET.get('status', '')
    program_filter = request.GET.get('program', '')
    region_filter = request.GET.get('region', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    search_query = request.GET.get('q', '')
    
    if status_filter:
        applications = applications.filter(status=status_filter)
    if program_filter:
        applications = applications.filter(program_id=program_filter)
    if region_filter:
        applications = applications.filter(applicant__region__icontains=region_filter)
    if date_from:
        applications = applications.filter(created_at__date__gte=date_from)
    if date_to:
        applications = applications.filter(created_at__date__lte=date_to)
    if search_query:
        applications = applications.filter(
            Q(applicant__user__first_name__icontains=search_query) |
            Q(applicant__user__last_name__icontains=search_query) |
            Q(applicant__user__email__icontains=search_query) |
            Q(applicant__national_id__icontains=search_query) |
            Q(id__icontains=search_query)
        )
    
    # -- Pagination --
    paginator = Paginator(applications.order_by('-created_at'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # -- Bulk Action Form --
    bulk_form = BulkActionForm()
    
    # -- Statistics --
    stats = {
        'total': ScholarshipApplication.objects.count(),
        'pending': ScholarshipApplication.objects.filter(status__in=['submitted', 'under_review', 'documents_pending']).count(),
        'approved': ScholarshipApplication.objects.filter(status='approved').count(),
        'rejected': ScholarshipApplication.objects.filter(status='rejected').count(),
    }
    
    programs = ScholarshipProgram.objects.filter(is_active=True)
    regions = ApplicantProfile.objects.values_list('region', flat=True).distinct().order_by('region')
    
    return render(request, 'scholarship/coordinator_dashboard.html', {
        'page_obj': page_obj,
        'bulk_form': bulk_form,
        'stats': stats,
        'programs': programs,
        'regions': regions,
        'status_choices': ScholarshipApplication.STATUS_CHOICES,
        'filters': {
            'status': status_filter,
            'program': program_filter,
            'region': region_filter,
            'date_from': date_from,
            'date_to': date_to,
            'q': search_query,
        }
    })


@login_required
@user_passes_test(is_coordinator)
def coordinator_application_detail(request, pk):
    """Coordinator view of any application with full audit trail."""
    application = get_object_or_404(
        ScholarshipApplication.objects.select_related('applicant__user', 'program', 'reviewed_by'),
        pk=pk
    )
    documents = application.documents.all()
    activity_logs = application.activity_logs.select_related('performed_by')
    education = application.applicant.education_records.all()
    
    if request.method == 'POST':
        status_form = StatusUpdateForm(request.POST, instance=application)
        if status_form.is_valid():
            old_status = application.status
            updated_app = status_form.save(commit=False)
            updated_app.reviewed_by = request.user
            updated_app.reviewed_at = timezone.now()
            updated_app.save()
            
            log_activity(
                application, 'status_changed', request.user,
                f'Status changed from {old_status} to {updated_app.status}',
                old_value=old_status,
                new_value=updated_app.status
            )
            messages.success(request, f'Application status updated to {updated_app.get_status_display()}.')
            return redirect('coordinator_application_detail', pk=pk)
    else:
        status_form = StatusUpdateForm(instance=application)
    
    return render(request, 'scholarship/coordinator_application_detail.html', {
        'application': application,
        'documents': documents,
        'activity_logs': activity_logs,
        'education': education,
        'status_form': status_form,
    })


@login_required
@user_passes_test(is_coordinator)
@require_POST
def bulk_action(request):
    """Process bulk actions on multiple applications."""
    form = BulkActionForm(request.POST)
    if form.is_valid():
        action = form.cleaned_data['action']
        app_ids = request.POST.get('application_ids', '').split(',')
        notes = form.cleaned_data['coordinator_notes']
        
        applications = ScholarshipApplication.objects.filter(pk__in=app_ids)
        updated_count = 0
        
        for app in applications:
            old_status = app.status
            app.status = action
            app.reviewed_by = request.user
            app.reviewed_at = timezone.now()
            if notes:
                app.coordinator_notes = notes
            app.save()
            
            log_activity(
                app, 'bulk_action', request.user,
                f'Bulk action: status changed to {action}',
                old_value=old_status,
                new_value=action
            )
            updated_count += 1
        
        messages.success(request, f'{updated_count} application(s) updated successfully.')
    else:
        messages.error(request, 'Invalid bulk action form.')
    
    return redirect('coordinator_dashboard')


@login_required
@user_passes_test(is_coordinator)
@require_POST
def verify_document(request, doc_id):
    """Coordinator verifies a KYC document."""
    document = get_object_or_404(KYCDocument, pk=doc_id)
    form = DocumentVerificationForm(request.POST, instance=document)
    
    if form.is_valid():
        old_status = document.verification_status
        doc = form.save(commit=False)
        doc.verified_by = request.user
        doc.verified_at = timezone.now()
        doc.save()
        
        log_activity(
            document.application, 'document_verified', request.user,
            f'Document "{document.get_document_type_display()}" verified: {old_status} -> {doc.verification_status}',
            old_value=old_status,
            new_value=doc.verification_status
        )
        messages.success(request, 'Document verification status updated.')
    
    return redirect('coordinator_application_detail', pk=document.application.pk)