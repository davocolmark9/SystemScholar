from django import template

register = template.Library()

@register.filter
def status_badge_class(status):
    """Returns Bootstrap badge class for application status."""
    classes = {
        'draft': 'bg-secondary',
        'submitted': 'bg-info',
        'under_review': 'bg-warning text-dark',
        'documents_pending': 'bg-warning',
        'approved': 'bg-success',
        'rejected': 'bg-danger',
        'disbursed': 'bg-primary',
    }
    return classes.get(status, 'bg-secondary')

@register.filter
def doc_status_badge_class(status):
    """Returns Bootstrap badge class for document verification status."""
    classes = {
        'pending': 'bg-warning text-dark',
        'verified': 'bg-success',
        'rejected': 'bg-danger',
    }
    return classes.get(status, 'bg-secondary')

@register.filter
def percentage(value, total):
    """Calculate percentage."""
    try:
        return round((value / total) * 100, 1) if total > 0 else 0
    except (TypeError, ZeroDivisionError):
        return 0
