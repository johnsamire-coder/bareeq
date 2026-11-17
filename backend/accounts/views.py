from rest_framework import generics, mixins, viewsets

from core.errors import BusinessError
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import HeardAboutOption, TermsVersion, User
from .permissions import IsManager
from .serializers import (
    AcceptTermsSerializer,
    HeardAboutSerializer,
    OtpRequestSerializer,
    OtpVerifySerializer,
    TechnicianSerializer,
    TermsSerializer,
    UserSerializer,
)
from .services import OtpError, accept_current_terms, request_otp, terms_outdated_settings, verify_otp


def _error(e: OtpError):
    return Response({"code": e.code, "detail": e.message}, status=e.status)


@api_view(["POST"])
@permission_classes([AllowAny])
def otp_request(request):
    s = OtpRequestSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    try:
        request_otp(**s.validated_data)
    except OtpError as e:
        return _error(e)
    return Response({"detail": "الكود اتبعت."})


@api_view(["POST"])
@permission_classes([AllowAny])
def otp_verify(request):
    s = OtpVerifySerializer(data=request.data)
    s.is_valid(raise_exception=True)
    data = dict(s.validated_data)
    phone, code = data.pop("phone"), data.pop("code")
    try:
        user, is_new = verify_otp(phone, code, signup=data)
    except OtpError as e:
        return _error(e)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "is_new": is_new, "user": UserSerializer(user).data})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    Token.objects.filter(user=request.user).delete()
    return Response({"detail": "اتسجل الخروج."})


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user


@api_view(["GET"])
@permission_classes([AllowAny])
def current_terms(request):
    terms = TermsVersion.current()
    if terms is None:
        return Response({"code": "terms_not_published", "detail": "الشروط لسه متنشرتش."}, status=404)
    return Response(TermsSerializer(terms).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def accept_terms(request):
    s = AcceptTermsSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    try:
        accept_current_terms(request.user, s.validated_data["terms_version"])
    except OtpError as e:
        return _error(e)
    return Response({"detail": "تمام."})


class HeardAboutListView(generics.ListAPIView):
    queryset = HeardAboutOption.objects.filter(is_active=True)
    serializer_class = HeardAboutSerializer
    permission_classes = [AllowAny]
    pagination_class = None


class TechnicianViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    """Manager adds technicians by phone number. Technicians cannot sign up themselves.
    No delete: set is_active=false to stop a technician (keeps his job history)."""

    queryset = User.objects.filter(role=User.Role.TECHNICIAN).order_by("full_name")
    serializer_class = TechnicianSerializer
    permission_classes = [IsManager]
    http_method_names = ["get", "post", "patch", "head", "options"]


@api_view(["GET"])
@permission_classes([IsManager])
def terms_status(request):
    """For the manager screens: do the published terms still match the settings?"""
    changed = terms_outdated_settings()
    current = TermsVersion.current()
    return Response(
        {
            "current_version": current.version if current else None,
            "needs_new_version": bool(changed) or current is None,
            "changed_settings": [{"key": s.key, "label": s.label, "value": s.value} for s in changed],
        }
    )


class ManagerHeardAboutViewSet(viewsets.ModelViewSet):
    """'How did you hear about us' list. No delete: hide with is_active=false."""

    permission_classes = [IsManager]
    queryset = HeardAboutOption.objects.all()
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_serializer_class(self):
        from rest_framework import serializers

        class S(serializers.ModelSerializer):
            class Meta:
                model = HeardAboutOption
                fields = ["id", "label", "sort_order", "is_active"]

        return S


@api_view(["GET", "POST"])
@permission_classes([IsManager])
def manager_terms(request):
    """GET: all versions (newest first). POST {text}: publish a new version.
    Customers must accept it before they continue (asked in the app)."""
    if request.method == "POST":
        text = (request.data.get("text") or "").strip()
        if len(text) < 50:
            raise BusinessError("text_too_short", "نص الشروط قصير قوي.")
        current = TermsVersion.current()
        if current and current.text.strip() == text:
            raise BusinessError("no_change", "النص زي النسخة الحالية بالظبط.")
        TermsVersion.objects.create(text=text, created_by=request.user)
    rows = [{"version": t.version, "text": t.text, "created_at": t.created_at,
             "accepted_by": t.acceptances.count()} for t in TermsVersion.objects.all()]
    return Response(rows, status=201 if request.method == "POST" else 200)
