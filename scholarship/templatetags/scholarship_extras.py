from django import template

register = template.Library()

@register.filter
def status_badge_class(status):
    classes = {
        'draft': 'bg-secondary-soft',
        'submitted': 'bg-info-soft',
        'under_review': 'bg-warning-soft',
        'approved': 'bg-success-soft',
        'rejected': 'bg-danger-soft',
        'pending': 'bg-warning-soft',
    }
    return classes.get(status, 'bg-secondary-soft')

@register.filter
def doc_status_badge_class(status):
    classes = {
        'pending': 'bg-warning-soft',
        'verified': 'bg-success-soft',
        'rejected': 'bg-danger-soft',
    }
    return classes.get(status, 'bg-secondary-soft')