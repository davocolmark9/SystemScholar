from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.exceptions import ValidationError
import re
import uuid


def validate_ph_phone(value):
    """Validate Philippine mobile number format."""
    pattern = r'^(?:\+63|0)?9\d{9}$'
    if not re.match(pattern, value):
        raise ValidationError('Enter a valid Philippine mobile number (e.g., 09171234567 or +639171234567).')


# ── Scholarship Program ──────────────────────────────────────────────────────
class ScholarshipProgram(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    deadline = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # NEW: Region eligibility (blank = nationwide)
    eligible_regions = models.CharField(
        max_length=200,
        blank=True,
        help_text="Comma-separated region codes (e.g., 'VI,VII,VIII'). Leave blank for nationwide."
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def is_region_eligible(self, region_code):
        """Check if a region code is eligible for this program."""
        if not self.eligible_regions:
            return True
        return region_code in self.eligible_regions.split(',')


# ── Applicant Profile ────────────────────────────────────────────────────────
class ApplicantProfile(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
        ('N', 'Prefer not to say'),
    ]

    # Philippine Regions
    PH_REGIONS = [
        ('NCR', 'National Capital Region (NCR)'),
        ('CAR', 'Cordillera Administrative Region (CAR)'),
        ('I', 'Region I - Ilocos'),
        ('II', 'Region II - Cagayan Valley'),
        ('III', 'Region III - Central Luzon'),
        ('IV-A', 'Region IV-A - CALABARZON'),
        ('IV-B', 'Region IV-B - MIMAROPA'),
        ('V', 'Region V - Bicol'),
        ('VI', 'Region VI - Western Visayas'),
        ('VII', 'Region VII - Central Visayas'),
        ('VIII', 'Region VIII - Eastern Visayas'),
        ('IX', 'Region IX - Zamboanga Peninsula'),
        ('X', 'Region X - Northern Mindanao'),
        ('XI', 'Region XI - Davao Region'),
        ('XII', 'Region XII - SOCCSKSARGEN'),
        ('XIII', 'Region XIII - Caraga'),
        ('BARMM', 'Bangsamoro Autonomous Region in Muslim Mindanao (BARMM)'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True, validators=[validate_ph_phone])
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=10, choices=PH_REGIONS, blank=True)
    country = models.CharField(max_length=50, default='Philippines', editable=False)
    national_id = models.CharField(max_length=50, blank=True, help_text="Philippine government-issued ID (e.g., UMID, Passport, Driver's License, PhilSys ID)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}"


# ── Educational Background (Formset Model) ──────────────────────────────────
class EducationalBackground(models.Model):
    DEGREE_CHOICES = [
        ('HS', 'High School'),
        ('DIP', 'Diploma'),
        ('BD', "Bachelor's Degree"),
        ('MD', "Master's Degree"),
        ('PHD', 'PhD / Doctorate'),
        ('CERT', 'Professional Certificate'),
    ]

    applicant = models.ForeignKey(ApplicantProfile, on_delete=models.CASCADE, related_name='education_records')
    institution_name = models.CharField(max_length=200)
    degree_type = models.CharField(max_length=4, choices=DEGREE_CHOICES)
    field_of_study = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    gpa = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    country = models.CharField(max_length=100, blank=True, default='Philippines')

    class Meta:
        ordering = ['-end_date', '-start_date']
        verbose_name_plural = 'Educational Backgrounds'

    def __str__(self):
        return f"{self.degree_type} at {self.institution_name}"


# ── Scholarship Application ─────────────────────────────────────────────────
class ScholarshipApplication(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('documents_pending', 'Documents Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('disbursed', 'Disbursed'),
    ]

    # Anti-IDOR: UUID as public identifier instead of sequential PK
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    applicant = models.ForeignKey(ApplicantProfile, on_delete=models.CASCADE, related_name='applications')
    program = models.ForeignKey(ScholarshipProgram, on_delete=models.CASCADE, related_name='applications')

    # Application content
    personal_statement = models.TextField(help_text="Why do you deserve this scholarship?")
    financial_need_statement = models.TextField(blank=True, help_text="Describe your financial situation")

    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_applications')
    coordinator_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        # Prevent duplicate applications to same program
        constraints = [
            models.UniqueConstraint(fields=['applicant', 'program'], condition=models.Q(status__in=['submitted', 'under_review', 'documents_pending', 'approved']), name='unique_active_application'),
        ]

    def __str__(self):
        return f"Application #{self.id} - {self.applicant} for {self.program}"

    def get_absolute_url(self):
        return reverse('application_detail', kwargs={'pk': self.pk})


# ── KYC Document Upload (Cloudinary) ────────────────────────────────────────
class KYCDocument(models.Model):
    DOCUMENT_TYPES = [
        ('national_id', 'Philippine National ID / UMID'),
        ('passport', 'Philippine Passport'),
        ('drivers_license', "Driver's License"),
        ('birth_cert', 'Philippine Birth Certificate (PSA)'),
        ('transcript', 'Academic Transcript (CHED/DepEd)'),
        ('income_proof', 'Proof of Income (BIR / Barangay Certificate)'),
        ('recommendation', 'Recommendation Letter'),
        ('other', 'Other Supporting Document'),
    ]

    VERIFICATION_STATUS = [
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected - Resubmit Required'),
    ]

    application = models.ForeignKey(ScholarshipApplication, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    # Cloudinary secure upload
    file = models.FileField(upload_to='kyc_documents/')
    file_name = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='pending')
    verification_notes = models.TextField(blank=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_documents')
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.get_document_type_display()} - {self.application}"


# ── Application Activity Log (Audit Trail) ───────────────────────────────
class ApplicationActivityLog(models.Model):
    ACTION_CHOICES = [
        ('created', 'Application Created'),
        ('updated', 'Application Updated'),
        ('submitted', 'Application Submitted'),
        ('status_changed', 'Status Changed'),
        ('document_uploaded', 'Document Uploaded'),
        ('document_verified', 'Document Verified'),
        ('note_added', 'Coordinator Note Added'),
        ('bulk_action', 'Bulk Action Applied'),
    ]

    application = models.ForeignKey(ScholarshipApplication, on_delete=models.CASCADE, related_name='activity_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField()
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.action} on {self.application} at {self.timestamp}"