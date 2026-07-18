from django.db import models


class AgencyScopedQuerySet(models.QuerySet):
    """QuerySet that provides agency-scoping for multi-tenant isolation."""

    def for_agency(self, agency):
        return self.filter(agency=agency)


class AgencyScopedManager(models.Manager):
    """
    Default manager for tenant-scoped models.

    Usage:
        class MyModel(models.Model):
            agency = models.ForeignKey(Agency, ...)
            objects = AgencyScopedManager()

    Then query with:
        MyModel.objects.for_agency(request_user_agency)
    """

    def get_queryset(self):
        return AgencyScopedQuerySet(self.model, using=self._db)

    def for_agency(self, agency):
        return self.get_queryset().for_agency(agency)
