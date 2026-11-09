
from django.db import models


class MediaFile(models.Model):

    class MediaType(models.TextChoices):
        VIDEO = 'video', 'Video'
        AUDIO = 'audio', 'Audio'

    title = models.CharField(max_length=255)

    file = models.FileField(upload_to='')

    media_type = models.CharField(
        max_length=10,
        choices=MediaType.choices
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']
