# NovaDownload

NovaDownload is a local Django application for downloading videos and audio from supported websites using yt-dlp.

## Features

- Download videos in available qualities and formats.
- Download audio as MP3.
- Support for websites supported by yt-dlp.
- Manage downloaded files in a media library.
- Delete downloaded files.
- Arabic and English interface.
- Responsive design.

## Requirements

- Python 3
- Django
- yt-dlp
- FFmpeg

## Installation

Clone the repository:

    git clone https://github.com/madara-yoo/NovaDownload.git
    cd NovaDownload

Create and activate a virtual environment:

    python -m venv .venv
    source .venv/bin/activate

Install dependencies:

    pip install -r requirements.txt

Install FFmpeg using your operating system package manager.

## Database Setup

    python manage.py migrate

## Run the Project

    python manage.py runserver

Open your browser: http://127.0.0.1:8000/

## Important Notes

- Intended for local development and use.
- Not currently configured for production hosting.
- Downloaded media and the local database are not included in this repository.
- Respect website terms and copyright laws.

## License

No license has been specified yet.
