from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from .models import (
    ScholarshipProgram, ApplicantProfile, EducationalBackground,
    ScholarshipApplication, KYCDocument
)


class AntiIDORTests(TestCase):
    """Test that users can ONLY access their own applications (Anti-IDOR)."""

    def setUp(self):
        # Create two users
        self.alice = User.objects.create_user('alice', 'alice@test.com', 'pass123')
        self.bob = User.objects.create_user('bob', 'bob@test.com', 'pass123')
        self.coordinator = User.objects.create_user('coordinator', 'coord@test.com', 'pass123', is_staff=True)

        # Create profiles
        self.alice_profile = ApplicantProfile.objects.create(user=self.alice)
        self.bob_profile = ApplicantProfile.objects.create(user=self.bob)

        # Create a program
        self.program = ScholarshipProgram.objects.create(
            name='Test Scholarship',
            description='Test',
            amount=1000.00,
            deadline=timezone.now().date() + timedelta(days=30),
        )

        # Create applications
        self.alice_app = ScholarshipApplication.objects.create(
            applicant=self.alice_profile,
            program=self.program,
            personal_statement='Alice statement',
            status='submitted',
            submitted_at=timezone.now(),
        )
        self.bob_app = ScholarshipApplication.objects.create(
            applicant=self.bob_profile,
            program=self.program,
            personal_statement='Bob statement',
            status='submitted',
            submitted_at=timezone.now(),
        )

    def test_alice_can_view_own_application(self):
        """Alice should see her own application detail."""
        self.client.login(username='alice', password='pass123')
        response = self.client.get(reverse('application_detail', kwargs={'pk': self.alice_app.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alice statement')

    def test_alice_cannot_view_bobs_application(self):
        """Anti-IDOR: Alice should get 404 when trying to view Bob's application."""
        self.client.login(username='alice', password='pass123')
        response = self.client.get(reverse('application_detail', kwargs={'pk': self.bob_app.pk}))
        self.assertEqual(response.status_code, 404)

    def test_alice_cannot_delete_bobs_document(self):
        """Anti-IDOR: Alice should get 404 when trying to delete Bob's document."""
        bob_doc = KYCDocument.objects.create(
            application=self.bob_app,
            document_type='national_id',
            file_name='bob_id.pdf'
        )
        self.client.login(username='alice', password='pass123')
        response = self.client.get(reverse('delete_document', kwargs={'doc_id': bob_doc.pk}))
        self.assertEqual(response.status_code, 404)

    def test_dashboard_only_shows_own_applications(self):
        """Dashboard should only show the logged-in user's applications."""
        self.client.login(username='alice', password='pass123')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alice statement')
        self.assertNotContains(response, 'Bob statement')

    def test_coordinator_can_view_any_application(self):
        """Coordinators should be able to view any application."""
        self.client.login(username='coordinator', password='pass123')
        response = self.client.get(reverse('coordinator_application_detail', kwargs={'pk': self.alice_app.pk}))
        self.assertEqual(response.status_code, 200)


class HoneypotTests(TestCase):
    """Test honeypot anti-spam on registration form."""

    def test_registration_with_honeypot_filled_is_blocked(self):
        """If honeypot field is filled, registration should fail."""
        response = self.client.post(reverse('register'), {
            'username': 'spambot',
            'first_name': 'Spam',
            'last_name': 'Bot',
            'email': 'spam@bot.com',
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!',
            'website': 'spam-site.com',  # Honeypot filled - should be rejected
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'website', 'Spam detected.')
        self.assertFalse(User.objects.filter(username='spambot').exists())

    def test_registration_without_honeypot_succeeds(self):
        """Normal registration without honeypot should succeed."""
        response = self.client.post(reverse('register'), {
            'username': 'legituser',
            'first_name': 'Legit',
            'last_name': 'User',
            'email': 'legit@user.com',
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!',
            'website': '',  # Honeypot empty - should pass
        })
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertTrue(User.objects.filter(username='legituser').exists())


class BulkActionTests(TestCase):
    """Test coordinator bulk actions."""

    def setUp(self):
        self.coordinator = User.objects.create_user('coord', 'coord@test.com', 'pass123', is_staff=True)
        self.applicant = User.objects.create_user('applicant', 'app@test.com', 'pass123')
        self.profile = ApplicantProfile.objects.create(user=self.applicant)
        self.program = ScholarshipProgram.objects.create(
            name='Test', description='Test', amount=1000,
            deadline=timezone.now().date() + timedelta(days=30)
        )
        self.app1 = ScholarshipApplication.objects.create(
            applicant=self.profile, program=self.program,
            personal_statement='Test', status='submitted', submitted_at=timezone.now()
        )
        self.app2 = ScholarshipApplication.objects.create(
            applicant=self.profile, program=self.program,
            personal_statement='Test2', status='submitted', submitted_at=timezone.now()
        )

    def test_bulk_approve(self):
        self.client.login(username='coord', password='pass123')
        response = self.client.post(reverse('bulk_action'), {
            'action': 'approved',
            'application_ids': f'{self.app1.pk},{self.app2.pk}',
            'coordinator_notes': 'Bulk approval test',
        })
        self.assertEqual(response.status_code, 302)
        self.app1.refresh_from_db()
        self.app2.refresh_from_db()
        self.assertEqual(self.app1.status, 'approved')
        self.assertEqual(self.app2.status, 'approved')
