from rest_framework import serializers
from scholarship.models import ScholarshipApplication, ApplicantProfile, KYCDocument, ScholarshipProgram

class ScholarshipProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScholarshipProgram
        fields = ['id', 'name', 'description', 'amount', 'deadline', 'is_active']

class KYCDocumentSerializer(serializers.ModelSerializer):
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    verification_status_display = serializers.CharField(source='get_verification_status_display', read_only=True)

    class Meta:
        model = KYCDocument
        fields = ['id', 'document_type', 'document_type_display', 'verification_status', 'verification_status_display', 'uploaded_at']

class ApplicantProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = ApplicantProfile
        fields = ['full_name', 'email', 'phone', 'city', 'region', 'country']

class ScholarshipApplicationSerializer(serializers.ModelSerializer):
    program = ScholarshipProgramSerializer(read_only=True)
    applicant = ApplicantProfileSerializer(read_only=True)
    documents = KYCDocumentSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ScholarshipApplication
        fields = [
            'id', 'program', 'applicant', 'status', 'status_display',
            'submitted_at', 'reviewed_at', 'documents', 'created_at'
        ]
