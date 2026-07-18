from django.db import models


class BHKChoices(models.TextChoices):
    STUDIO = "studio", "Studio"
    ONE_BHK = "1_bhk", "1 BHK"
    TWO_BHK = "2_bhk", "2 BHK"
    THREE_BHK = "3_bhk", "3 BHK"
    FOUR_BHK = "4_bhk", "4 BHK"
    FOUR_PLUS_BHK = "4_plus_bhk", "4+ BHK"
