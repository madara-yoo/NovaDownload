import os
import uuid
import time
import glob
import logging
import threading

import yt_dlp

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.db import close_old_connections
from django.views.decorators.http import require_POST

from .models import MediaFile


logger = logging.getLogger(__name__)

download_tasks = {}
tasks_lock = threading.Lock()


def update_task(task_id, **data):
    with tasks_lock:
        if task_id in download_tasks:
            download_tasks[task_id].update(data)


def home(request):
    return render(request, 'downloader/home.html')


def library(request):
    videos = MediaFile.objects.filter(media_type='video')
    audios = MediaFile.objects.filter(media_type='audio')

    return render(request, 'downloader/library.html', {
        'videos': videos,
        'audios': audios,
    })


def run_download(task_id, url, media_type, quality):

    close_old_connections()

    try:
        if media_type == 'mp3':
            output_dir = os.path.join(settings.MEDIA_ROOT, 'mp3')
        else:
            output_dir = os.path.join(settings.MEDIA_ROOT, 'videos')

        os.makedirs(output_dir, exist_ok=True)

        options = {
            'outtmpl': os.path.join(
                output_dir,
                '%(title).150B [%(id)s].%(ext)s'
            ),
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
        }

        if media_type == 'mp3':

            options.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })

        else:

            heights = {
                'best': None,
                '1080': 1080,
                '720': 720,
                '480': 480,
                '360': 360,
            }

            height = heights[quality]

            if height:
                options['format'] = f'best[height<={height}]/best'
            else:
                options['format'] = 'best'

            options['merge_output_format'] = 'mp4'

        def progress_hook(data):

            status = data.get('status')

            if status == 'downloading':

                downloaded = data.get('downloaded_bytes', 0) or 0

                total = (
                    data.get('total_bytes')
                    or data.get('total_bytes_estimate')
                    or 0
                )

                percent = 0

                if total:
                    percent = min(
                        99,
                        round(downloaded / total * 100, 1)
                    )

                update_task(
                    task_id,
                    status='downloading',
                    percent=percent,
                    downloaded=downloaded,
                    total=total,
                    speed=data.get('speed') or 0,
                    eta=data.get('eta'),
                    message='Downloading...'
                )

            elif status == 'finished':

                update_task(
                    task_id,
                    status='processing',
                    percent=99,
                    message='Processing file...'
                )

        options['progress_hooks'] = [progress_hook]

        update_task(
            task_id,
            status='starting',
            message='Connecting to source...'
        )

        with yt_dlp.YoutubeDL(options) as ydl:

            info = ydl.extract_info(url, download=True)

            if not info:
                raise Exception('No video information returned.')

            title = info.get('title') or 'Downloaded file'

            filepath = None

            if media_type == 'mp3':

                requested = ydl.prepare_filename(info)
                base_path = os.path.splitext(requested)[0]
                mp3_path = base_path + '.mp3'

                if os.path.isfile(mp3_path):
                    filepath = mp3_path

                else:
                    video_id = info.get('id')

                    if video_id:
                        pattern = os.path.join(
                            output_dir,
                            '* [{}].mp3'.format(glob.escape(video_id))
                        )

                        files = glob.glob(pattern)

                        if files:
                            filepath = max(
                                files,
                                key=os.path.getmtime
                            )

            else:

                video_id = info.get('id')

                if not video_id:
                    raise Exception(
                        'Could not identify downloaded video.'
                    )

                pattern = os.path.join(
                    output_dir,
                    '* [{}].*'.format(glob.escape(video_id))
                )

                files = glob.glob(pattern)

                valid_extensions = (
                    '.mp4', '.mkv', '.webm'
                )

                files = [
                    path for path in files
                    if os.path.isfile(path)
                    and path.lower().endswith(valid_extensions)
                ]

                if files:
                    filepath = max(
                        files,
                        key=os.path.getmtime
                    )

            if not filepath or not os.path.isfile(filepath):
                raise Exception(
                    'Download finished, but the final file was not found.'
                )

            relative_path = os.path.relpath(
                filepath,
                settings.MEDIA_ROOT
            )

            MediaFile.objects.create(
                title=title,
                file=relative_path,
                media_type='audio' if media_type == 'mp3' else 'video',
            )

        update_task(
            task_id,
            status='completed',
            percent=100,
            message='Download completed successfully!'
        )

    except Exception as error:

        logger.exception('DOWNLOAD FAILED')

        update_task(
            task_id,
            status='failed',
            message=str(error)
        )

    finally:
        close_old_connections()


def start_download(request):

    if request.method != 'POST':
        return JsonResponse({
            'error': 'POST method required.'
        }, status=405)

    url = request.POST.get('video_url', '').strip()
    media_type = request.POST.get('format', 'mp4')
    quality = request.POST.get('quality', 'best')

    if not url:
        return JsonResponse({
            'error': 'Please enter a video URL.'
        }, status=400)

    if media_type not in ('mp4', 'mp3'):
        return JsonResponse({
            'error': 'Invalid format.'
        }, status=400)

    if quality not in ('best', '1080', '720', '480', '360'):
        return JsonResponse({
            'error': 'Invalid quality.'
        }, status=400)

    task_id = str(uuid.uuid4())

    with tasks_lock:
        download_tasks[task_id] = {
            'status': 'queued',
            'percent': 0,
            'downloaded': 0,
            'total': 0,
            'speed': 0,
            'eta': None,
            'message': 'Waiting to start...'
        }

    thread = threading.Thread(
        target=run_download,
        args=(task_id, url, media_type, quality),
        daemon=True
    )

    thread.start()

    return JsonResponse({
        'task_id': task_id
    })


def download_status(request, task_id):

    if request.method != 'GET':
        return JsonResponse({
            'error': 'GET method required.'
        }, status=405)

    with tasks_lock:
        task = download_tasks.get(task_id)

        if task is None:
            return JsonResponse({
                'error': 'Download task not found.'
            }, status=404)

        result = task.copy()

    return JsonResponse(result)

@require_POST
def delete_media(request, pk):
    item = get_object_or_404(MediaFile, pk=pk)

    try:
        if item.file:
            item.file.delete(save=False)

        item.delete()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'File deleted successfully.'
            })

        return redirect('library')

    except Exception as error:
        logger.exception('MEDIA DELETE FAILED')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': str(error)
            }, status=500)

        raise