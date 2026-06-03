from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.forms.models import inlineformset_factory
from django.utils import timezone
from .models import (
    ApplicantProfile, EducationalBackground, ScholarshipApplication,
    ScholarshipProgram, KYCDocument
)

# ── Honeypot Anti-Spam Registration Form ────────────────────────────────────
class HoneypotRegistrationForm(UserCreationForm):
    """
    Registration form with honeypot field to block automated spam bots.
    The honeypot field is hidden via CSS and should never be filled by humans.
    """
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'your.email@example.com'
    }))
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'First Name'
    }))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Last Name'
    }))

    # HONEYPOT FIELD - hidden from humans, visible to bots
    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'style': 'position:absolute;left:-9999px;top:-9999px;',
            'tabindex': '-1',
            'autocomplete': 'off',
        }),
        label='',
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
        }

    def clean_website(self):
        """If honeypot field is filled, reject as spam."""
        honeypot = self.cleaned_data.get('website')
        if honeypot:
            raise forms.ValidationError("Spam detected. Please do not fill hidden fields.")
        return honeypot

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

# ── Applicant Profile Form ──────────────────────────────────────────────────
class ApplicantProfileForm(forms.ModelForm):
    class Meta:
        model = ApplicantProfile
        fields = ['phone', 'date_of_birth', 'gender', 'address', 'city', 'region', 'country', 'national_id']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1 234 567 8900'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Street address'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'region': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State / Region'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country'}),
            'national_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'National ID / Passport Number'}),
        }

# ── Educational Background Form (for Formsets) ──────────────────────────────
class EducationalBackgroundForm(forms.ModelForm):
    class Meta:
        model = EducationalBackground
        fields = ['institution_name', 'degree_type', 'field_of_study', 'start_date', 'end_date', 'is_current', 'gpa', 'country']
        widgets = {
            'institution_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'University / School Name'}),
            'degree_type': forms.Select(attrs={'class': 'form-select'}),
            'field_of_study': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Computer Science'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_current': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'gpa': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '4.0'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country of Institution'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        is_current = cleaned_data.get('is_current')

        if end_date and start_date and end_date < start_date:
            raise forms.ValidationError("End date cannot be before start date.")

        if is_current and end_date:
            raise forms.ValidationError("Current education should not have an end date.")

        return cleaned_data

# Create the inline formset factory
EducationalBackgroundFormSet = inlineformset_factory(
    ApplicantProfile,
    EducationalBackground,
    form=EducationalBackgroundForm,
    extra=2,  # Show 2 empty forms by default
    can_delete=True,
    min_num=1,
    validate_min=True,
    max_num=5,
    validate_max=True,
)

# ── Scholarship Application Form ────────────────────────────────────────────
class ScholarshipApplicationForm(forms.ModelForm):
    class Meta:
        model = ScholarshipApplication
        fields = ['program', 'personal_statement', 'financial_need_statement']
        widgets = {
            'program': forms.Select(attrs={'class': 'form-select'}),
            'personal_statement': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Describe your academic goals, achievements, and why you deserve this scholarship...'
            }),
            'financial_need_statement': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe your financial situation and how this scholarship would help you...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active programs
        self.fields['program'].queryset = ScholarshipProgram.objects.filter(is_active=True, deadline__gte=timezone.now().date())
        self.fields['program'].empty_label = "Select a Scholarship Program"

# ── KYC Document Upload Form ────────────────────────────────────────────────
class KYCDocumentForm(forms.ModelForm):
    class Meta:
        model = KYCDocument
        fields = ['document_type', 'file']
        widgets = {
            'document_type': forms.Select(attrs={'class': 'form-select'}),
            'file': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}),
        }

# ── Coordinator Bulk Action Form ────────────────────────────────────────────
class BulkActionForm(forms.Form):
    ACTION_CHOICES = [
        ('under_review', 'Mark as Under Review'),
        ('documents_pending', 'Request Documents'),
        ('approved', 'Approve Applications'),
        ('rejected', 'Reject Applications'),
    ]

    action = forms.ChoiceField(choices=ACTION_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    application_ids = forms.CharField(widget=forms.HiddenInput())
    coordinator_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Add notes for selected applicants...'})
    )

# ── Coordinator Status Update Form ──────────────────────────────────────────
class StatusUpdateForm(forms.ModelForm):
    class Meta:
        model = ScholarshipApplication
        fields = ['status', 'coordinator_notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'coordinator_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

# ── Document Verification Form ──────────────────────────────────────────────
class DocumentVerificationForm(forms.ModelForm):
    class Meta:
        model = KYCDocument
        fields = ['verification_status', 'verification_notes']
        widgets = {
            'verification_status': forms.Select(attrs={'class': 'form-select'}),
            'verification_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class BootstrapFormMixin:
    """Mixin to add Bootstrap classes to form fields."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, (forms.TextInput, forms.EmailInput, 
                                         forms.PasswordInput, forms.NumberInput,
                                         forms.DateInput, forms.Select)):
                field.widget.attrs.update({
                    'class': 'form-control'
                })
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'rows': 4
                })
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({
                    'class': 'form-check-input'
                })
            elif isinstance(field.widget, forms.FileInput):
                field.widget.attrs.update({
                    'class': 'form-control'
                })
