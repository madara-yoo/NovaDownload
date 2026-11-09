from django.contrib import admin
from .models import MediaFile


@admin.register(MediaFile)
class MediaFileAdmin(admin.ModelAdmin):

    list_display = (
        'title',
        'media_type',
        'created_at',
    )

    list_filter = ('media_type', 'created_at')

    search_fields = ('title',)

    ordering = ('-created_at',)