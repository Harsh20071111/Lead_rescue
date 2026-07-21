import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django; django.setup()

import cloudinary.api
from apps.properties.models import PropertyImage
from apps.properties.models import Property

print("Deleting all property images from Cloudinary...")
for img in PropertyImage.objects.iterator():
    try:
        if img.image:
            public_id = getattr(img.image, "public_id", None) or str(img.image)
            cloudinary.api.delete_resources([public_id])
            print(f"  Deleted: {public_id}")
    except Exception as e:
        print(f"  Error deleting {img.image}: {e}")

print("Deleting all brochures from Cloudinary...")
for prop in Property.objects.exclude(brochure_pdf__isnull=True).exclude(brochure_pdf=""):
    try:
        cloudinary.api.delete_resources([prop.brochure_pdf], resource_type="raw")
        print(f"  Deleted brochure: {prop.brochure_pdf}")
    except Exception as e:
        print(f"  Error deleting brochure {prop.brochure_pdf}: {e}")

print("\nDeleting entire property_images folder...")
try:
    result = cloudinary.api.delete_resources_by_prefix("property_images/")
    print(f"  Result: {result}")
except Exception as e:
    print(f"  Error: {e}")

print("\nDeleting entire brochures folder...")
try:
    result = cloudinary.api.delete_resources_by_prefix("brochures/", resource_type="raw")
    print(f"  Result: {result}")
except Exception as e:
    print(f"  Error: {e}")

print("\nDone!")
