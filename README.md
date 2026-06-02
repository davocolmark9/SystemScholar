# Regional Scholarship Application Portal

A secure digital hub for processing student scholarship applications. Built with Django, featuring Cloudinary document uploads, formsets for educational records, Anti-IDOR protection, honeypot anti-spam, and JWT-secured API for external institutions.

## Features

### For Applicants
- **Secure Registration** with honeypot anti-spam protection
- **Profile Management** with personal details and contact information
- **Educational Background Formsets** - Add up to 5 academic records simultaneously
- **KYC Document Upload** via Cloudinary (secure, encrypted storage)
- **Application Tracking** with real-time status updates and audit trail
- **Anti-IDOR Protection** - Students can ONLY view their own applications using UUID identifiers

### For Regional Coordinators
- **Backend Dashboard** with filtering by status, program, region, and date range
- **Search** across applicant names, emails, national IDs, and application IDs
- **Bulk Actions** - Approve, reject, or request documents for multiple applications
- **Document Verification** - Verify/reject KYC documents individually
- **Full Audit Trail** - Every action logged with timestamp, user, and IP address

### API (External Institutions)
- **JWT Authentication** via `djangorestframework-simplejwt`
- **Applicant Status Verification** endpoint
- **"Restricted Data"** response for unauthenticated requests
- Bearer token required in `Authorization` header

## Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | Django 6.0.5 |
| API | Django REST Framework + SimpleJWT |
| Database | PostgreSQL (production) / SQLite (development) |
| File Storage | Cloudinary |
| Frontend | Bootstrap 5 + Bootstrap Icons |
| Auth | Django built-in + JWT for API |

## Project Structure

```
scholarship_portal/
├── scholarship/              # Main app
│   ├── models.py             # ScholarshipProgram, ApplicantProfile, EducationalBackground, ScholarshipApplication, KYCDocument, ApplicationActivityLog
│   ├── forms.py              # HoneypotRegistrationForm, EducationalBackgroundFormSet, etc.
│   ├── views.py              # Applicant views + Coordinator views (with @user_passes_test)
│   ├── urls.py               # URL routing
│   ├── templates/scholarship/  # All HTML templates
│   └── templatetags/         # Custom template filters (status badges, etc.)
├── api/                      # REST API app
│   ├── views.py              # JWT-secured verify endpoint
│   ├── serializers.py        # DRF serializers
│   ├── permissions.py        # IsExternalInstitution permission
│   └── urls.py               # API URL patterns
├── scholarship_project/      # Project config
│   ├── settings.py           # DRF + JWT settings
│   └── urls.py               # Root URLconf
└── templates/
    └── base.html             # Base template with Bootstrap 5
```

## Security Features

### 1. Anti-IDOR (Insecure Direct Object Reference)
- Applications use **UUID primary keys** instead of sequential integers
- Every applicant view scopes queries to `request.user`: `get_object_or_404(..., applicant=profile)`
- Students cannot access other applicants' data by manipulating URLs

### 2. Honeypot Anti-Spam
- Registration form includes a hidden `website` field
- If filled (by bots), form validation rejects submission
- Field hidden via CSS (`position:absolute;left:-9999px`)

### 3. JWT-Secured API
```bash
# Get token
curl -X POST /api/token/ -d "username=institution&password=pass"

# Verify applicant (authenticated)
curl -H "Authorization: Bearer <access_token>" /api/verify/<uuid>/

# Unauthenticated request returns:
# {"message": "Restricted Data", "detail": "Authentication required..."}
```

### 4. Audit Trail
- Every status change, document upload, and bulk action is logged
- Logs include: action type, user, timestamp, IP address, old/new values
- Immutable history for compliance

## Setup & Deployment

### Local Development
```bash
# Clone and setup
cd scholarship_portal
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Environment variables (or use .env)
cp .env.example .env
# Edit .env with your Cloudinary and DB credentials

# Database
python manage.py migrate
python manage.py createsuperuser

# Run
python manage.py runserver
```

### Render Deployment
```bash
# The build.sh script handles:
# - pip install
# - collectstatic
# - migrate
# - createsuperuser (auto, no input)
```

Set these environment variables on Render:
- `SECRET_KEY`
- `DATABASE_URL`
- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`
- `ALLOWED_HOSTS`
- `RENDER_EXTERNAL_HOSTNAME`

### Creating a Coordinator Account
```bash
python manage.py shell
>>> from django.contrib.auth.models import User
>>> User.objects.create_user('coordinator', 'coord@example.com', 'password', is_staff=True)
```

## API Usage for External Institutions

### 1. Obtain JWT Token
```bash
curl -X POST https://your-domain.com/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "institution_user", "password": "password"}'
```

Response:
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### 2. Verify Applicant Status
```bash
curl -X GET https://your-domain.com/api/verify/<application-uuid>/ \
  -H "Authorization: Bearer <access_token>"
```

Response (authenticated):
```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "program": {"name": "STEM Excellence Scholarship", ...},
    "applicant": {"full_name": "Jane Doe", "email": "jane@example.com", ...},
    "status": "approved",
    "status_display": "Approved",
    "submitted_at": "2026-06-01T10:00:00Z",
    ...
  }
}
```

Response (unauthenticated):
```json
{
  "success": false,
  "message": "Restricted Data",
  "detail": "Authentication required. Please provide a valid JWT Bearer token..."
}
```

### 3. Refresh Token
```bash
curl -X POST https://your-domain.com/api/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "<refresh_token>"}'
```

## Running Tests

```bash
python manage.py test scholarship.tests
```

Tests cover:
- Anti-IDOR protection (cross-user access attempts)
- Honeypot spam blocking
- Bulk action processing
- Application lifecycle

## License
MIT License
