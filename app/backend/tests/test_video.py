"""Regression test: the MJPEG stream must never be cacheable by the browser.

An <img src="/api/stream/video"> unmounts/remounts on every navigation away
from and back to the live view. If this response were cacheable, the new
element would render the browser's cached copy -- a single frozen frame --
instead of opening a fresh connection to the live stream.

Calls the route function directly rather than going through TestClient: its
body is an infinite generator (by design -- it's a never-ending MJPEG feed),
and driving it through a real HTTP round-trip would mean actually consuming
that infinite stream just to inspect headers.
"""

from app.backend.routers.video import stream_video


def test_stream_video_is_not_cacheable(fake_pipeline):
    response = stream_video(pipeline=fake_pipeline)
    cache_control = response.headers["cache-control"]
    assert "no-store" in cache_control
    assert "no-cache" in cache_control
