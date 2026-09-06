"""
Reading and setting the customer's own marks.

Two different audiences, so two different gates, and they are deliberately not
symmetrical: **everyone signed in reads branding, only an Admin writes it.**
The logo is on every screen of the product, so gating the read on a capability
would mean the top bar renders blank for four of the five roles -- the correct
read capability here is "is signed in".

The write is `BRANDING_MANAGE`, which is Admin-only. That is narrower than it
strictly has to be and is meant to be: the logo is the one thing on screen that
tells a viewer whose system this is, and a role that can change it can make the
product claim to be somebody else.
"""

import base64

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts import capabilities as caps
from accounts.permissions import RequiresCapability
from accounts.security import AuditLog

from .models import Branding

CAP = RequiresCapability(read=None, write=caps.BRANDING_MANAGE)

#: Image formats a browser will render inline from a data URI without argument.
ALLOWED_MIME = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/svg+xml": ".svg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}

#: Roughly 2 MB of decoded image. A mark drawn for a 46px bar and a background
#: wash does not need more, and the row is read on every page load.
MAX_BYTES = 2 * 1024 * 1024


class BrandingSerializer(serializers.ModelSerializer):
    logo = serializers.SerializerMethodField()
    watermark = serializers.SerializerMethodField()

    class Meta:
        model = Branding
        fields = ["app_name", "company_name", "logo", "watermark",
                  "logo_filename", "watermark_filename", "watermark_opacity",
                  "updated_at"]

    def get_logo(self, obj):
        return obj.data_uri("logo")

    def get_watermark(self, obj):
        # Falling back to the logo is what makes the background mark work for
        # the common case of a company with exactly one image file.
        return obj.data_uri("watermark") or obj.data_uri("logo")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def branding_view(request):
    return Response(BrandingSerializer(Branding.load()).data)


def _decode(payload, filename):
    """A data URI or bare base64 as (bytes, mime), or an error string."""
    if not payload:
        return None, None, None
    raw = payload
    mime = ""
    if raw.startswith("data:"):
        header, _, raw = raw.partition(",")
        mime = header[5:].split(";")[0].strip().lower()
    if not mime:
        ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
        mime = next((m for m, e in ALLOWED_MIME.items() if e == ext), "image/png")
    if mime not in ALLOWED_MIME:
        return None, None, "%s is not an image format the browser will show." % mime
    try:
        data = base64.b64decode(raw, validate=True)
    except Exception:                            # noqa: BLE001
        return None, None, "That file did not arrive intact. Try again."
    if len(data) > MAX_BYTES:
        return None, None, ("That image is %.1f MB. The limit is 2 MB."
                            % (len(data) / 1024 / 1024))
    return base64.b64encode(data).decode("ascii"), mime, None


@api_view(["PUT", "PATCH"])
@permission_classes([CAP])
def branding_update_view(request):
    """
    Set the marks, the names, or the wash strength.

    Every field is optional and absent means "leave it alone", so the screen
    can save a renamed company without re-uploading two images. Clearing is
    explicit -- an empty string for an image field removes it -- because
    "absent" and "cleared" are different intentions and conflating them makes
    the logo impossible to remove once set.
    """
    branding = Branding.load()
    changed = []

    for field in ("app_name", "company_name"):
        if field in request.data:
            value = (request.data.get(field) or "").strip()
            if field == "app_name" and not value:
                return Response(
                    {"detail": "The application needs a name in the top bar."},
                    status=status.HTTP_400_BAD_REQUEST)
            setattr(branding, field, value)
            changed.append(field)

    if "watermark_opacity" in request.data:
        try:
            opacity = int(request.data.get("watermark_opacity"))
        except (TypeError, ValueError):
            return Response({"detail": "Wash strength must be a whole number."},
                            status=status.HTTP_400_BAD_REQUEST)
        if not 0 <= opacity <= 40:
            return Response(
                {"detail": "Wash strength runs from 0 to 40 percent."},
                status=status.HTTP_400_BAD_REQUEST)
        branding.watermark_opacity = opacity
        changed.append("watermark_opacity")

    for which in ("logo", "watermark"):
        key = "%s_b64" % which
        if key not in request.data:
            continue
        payload = request.data.get(key) or ""
        filename = (request.data.get("%s_filename" % which) or "").strip()
        if not payload:
            setattr(branding, key, "")
            setattr(branding, "%s_mime" % which, "")
            setattr(branding, "%s_filename" % which, "")
            changed.append("%s cleared" % which)
            continue
        content, mime, error = _decode(payload, filename)
        if error:
            return Response({"detail": error},
                            status=status.HTTP_400_BAD_REQUEST)
        setattr(branding, key, content)
        setattr(branding, "%s_mime" % which, mime)
        setattr(branding, "%s_filename" % which, filename or "%s%s" % (
            which, ALLOWED_MIME[mime]))
        changed.append(which)

    branding.updated_by = request.user if request.user.is_authenticated else None
    branding.save()

    AuditLog.write(request, AuditLog.BRANDING_CHANGED,
                   "Updated branding: %s" % (", ".join(changed) or "no change"),
                   target=branding)
    return Response(BrandingSerializer(branding).data)
