from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.shortcuts import get_object_or_404
from scholarship.models import ScholarshipApplication
from .serializers import ScholarshipApplicationSerializer
from .permissions import IsExternalInstitution


@api_view(['GET'])
@permission_classes([IsExternalInstitution])
def verify_applicant_status(request, application_id):
    """
    JWT-secured API endpoint for external academic institutions to verify
    the status of an applicant.

    Returns full data for authenticated JWT requests.
    Returns "Restricted Data" for unauthenticated requests.

    URL: /api/verify/<uuid:application_id>/
    Headers: Authorization: Bearer <jwt_access_token>
    """
    try:
        application = get_object_or_404(ScholarshipApplication, pk=application_id)
        serializer = ScholarshipApplicationSerializer(application)
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def verify_applicant_status_public(request, application_id):
    """
    Public endpoint that returns "Restricted Data" for unauthenticated requests.
    This demonstrates the security boundary - no JWT = no real data.
    """
    return Response({
        'success': False,
        'message': 'Restricted Data',
        'detail': 'Authentication required. Please provide a valid JWT Bearer token in the Authorization header.'
    }, status=status.HTTP_401_UNAUTHORIZED)
