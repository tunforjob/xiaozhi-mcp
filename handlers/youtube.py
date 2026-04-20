import re
from typing import Any
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import NoTranscriptFound, TranscriptsDisabled, YouTubeTranscriptApi


_PREFERRED_LANGS = ['ru', 'uk', 'en']


def _extract_video_id(url_or_id: str) -> str | None:
    url_or_id = url_or_id.strip()

    if re.match(r'^[a-zA-Z0-9_-]{11}$', url_or_id):
        return url_or_id

    m = re.search(
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        url_or_id,
    )
    if m:
        return m.group(1)

    parsed = urlparse(url_or_id)
    qs = parse_qs(parsed.query)
    if 'v' in qs:
        return qs['v'][0]

    return None


def _snippets_to_text(fetched) -> str:
    return ' '.join(s.text.strip() for s in fetched if s.text)


async def get_youtube_transcript(url_or_id: str) -> dict[str, Any]:
    video_id = _extract_video_id(url_or_id)
    if not video_id:
        return {'status': 'error', 'error': f'Could not extract video ID from: {url_or_id}'}

    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)

        transcript = None
        lang_used = None

        for lang in _PREFERRED_LANGS:
            try:
                transcript = transcript_list.find_transcript([lang])
                lang_used = transcript.language_code
                break
            except NoTranscriptFound:
                pass

        if transcript is None:
            try:
                transcript = transcript_list.find_generated_transcript(_PREFERRED_LANGS)
                lang_used = transcript.language_code + ' (auto)'
            except NoTranscriptFound:
                available = (
                    transcript_list._manually_created_transcripts
                    or transcript_list._generated_transcripts
                )
                if available:
                    transcript = next(iter(available.values()))
                    lang_used = transcript.language_code

        if transcript is None:
            return {'status': 'error', 'error': 'No subtitles available for this video'}

        fetched = transcript.fetch()
        text = _snippets_to_text(fetched)

        return {
            'status': 'ok',
            'video_id': video_id,
            'language': lang_used,
            'transcript': text,
            'char_count': len(text),
        }

    except TranscriptsDisabled:
        return {'status': 'error', 'error': 'Subtitles are disabled for this video'}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}
