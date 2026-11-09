from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),

    path('library/', views.library, name='library'),

    path(
        'download/',
        views.start_download,
        name='download'
    ),

    path(
        'download-status/<str:task_id>/',
        views.download_status,
        name='download_status'
    ),

    path(
        'delete/<int:pk>/',
        views.delete_media,
        name='delete_media'
    ),
]