"""Before/after photos: checked, shrunk to 1600 px, stored with their evidence data."""
import hashlib
import io
import uuid

from django.core.files.base import ContentFile
from django.utils import timezone
from PIL import Image, ImageOps, UnidentifiedImageError

from core.errors import BusinessError
from core.services import get_setting
from scheduling.travel import distance_km

from .models import Order, OrderPhoto

MAX_SIDE = 1600
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # technical limit, not a business number

# Which photos are allowed at which job status.
STAGE_STATUS = {
    OrderPhoto.Stage.BEFORE: Order.Status.ARRIVED,
    OrderPhoto.Stage.AFTER: Order.Status.IN_PROGRESS,
}


def shrink(data):
    try:
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)  # keep the photo upright
        img = img.convert("RGB")
    except (UnidentifiedImageError, OSError):
        raise BusinessError("not_an_image", "الملف ده مش صورة.")
    img.thumbnail((MAX_SIDE, MAX_SIDE))  # only ever makes it smaller
    out = io.BytesIO()
    img.save(out, "JPEG", quality=85)
    return out.getvalue(), img.size


def add_photo(order, technician, stage, side, data, captured_at, lat, lng, accuracy_m=None):
    order = Order.objects.get(pk=order.pk)  # always the current status
    if order.technician_id != technician.id:
        raise BusinessError("not_your_job", "الطلب ده مش بتاعك.", status=403)
    if stage not in OrderPhoto.Stage.values or side not in OrderPhoto.Side.values:
        raise BusinessError("bad_photo_kind", "نوع الصورة مش صحيح.")
    if order.status != STAGE_STATUS[stage]:
        raise BusinessError("wrong_time_for_photo", "مينفعش تصور الصور دي دلوقتي.")
    if captured_at is None or lat is None or lng is None:
        raise BusinessError("photo_data_missing", "لازم وقت التصوير والمكان مع الصورة.")
    if not data or len(data) > MAX_UPLOAD_BYTES:
        raise BusinessError("bad_size", "حجم الصورة مش مقبول.")

    now = timezone.now()
    flags = []
    if (now - captured_at).total_seconds() > get_setting("photos-max-age-minutes") * 60:
        flags.append("taken_long_before_upload")
    if (captured_at - now).total_seconds() > 120:
        flags.append("time_in_future")
    if distance_km((lat, lng), order.place) * 1000 > get_setting("photos-max-distance-meters"):
        flags.append("far_from_address")

    photo = OrderPhoto(
        order=order, stage=stage, side=side, taken_by=technician, captured_at=captured_at, uploaded_at=now,
        lat=lat, lng=lng, accuracy_m=accuracy_m, original_sha256=hashlib.sha256(data).hexdigest(), flags=flags,
    )
    jpeg, (photo.width, photo.height) = shrink(data)
    photo.image.save(f"{stage}-{side}-{uuid.uuid4().hex}.jpg", ContentFile(jpeg), save=False)
    photo.save()
    return photo


def has_all_sides(order, stage):
    taken = set(order.photos.filter(stage=stage).values_list("side", flat=True))
    return taken >= set(OrderPhoto.Side.values)
