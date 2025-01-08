from django.db import models
from django.utils import timezone
import datetime

class InstagramUser(models.Model):
    username = models.CharField(max_length=255, blank=True, null=True)
    password = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    bio_link = models.URLField(blank=True, null=True)
    is_master = models.BooleanField(default=False)

    class Meta:
        db_table = 'instagram_user'

    def __str__(self):
        return self.name or self.username or "Unknown User"

class Publication(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    image = models.ImageField(upload_to='uploads/', null=True, blank=True)
    date_posted = models.DateTimeField(auto_now_add=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    is_published = models.BooleanField(default=False)
    instagram_user = models.ForeignKey(
        InstagramUser, on_delete=models.CASCADE, related_name='publication'
    )
    class Meta:
        db_table = 'Publication'

    def save(self, *args, **kwargs):
        if self.scheduled_at and self.scheduled_at.tzinfo is not None:
            self.scheduled_at = self.scheduled_at.replace(tzinfo=None)
            self.scheduled_at = timezone.make_aware(self.scheduled_at)

        if not self.scheduled_at or self.scheduled_at <= timezone.now():
            self.is_published = True
            self.published_at = timezone.now()

        super().save(*args, **kwargs)