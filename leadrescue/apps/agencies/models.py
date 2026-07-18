from django.db import models
from django.utils.text import slugify


class Agency(models.Model):
    class PlanTier(models.TextChoices):
        FREE = "free", "Free"
        STARTER = "starter", "Starter"
        PRO = "pro", "Pro"

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    owner_phone = models.CharField(max_length=20)
    owner_email = models.EmailField()
    city = models.CharField(max_length=100)

    plan_tier = models.CharField(
        max_length=20,
        choices=PlanTier.choices,
        default=PlanTier.FREE,
    )
    brand_logo = models.ImageField(
        upload_to="agency_logos/", blank=True, null=True
    )
    brand_primary_color = models.CharField(
        max_length=7, default="#B87333", blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "agencies"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or "agency"
            slug = base_slug
            counter = 1
            while Agency.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
