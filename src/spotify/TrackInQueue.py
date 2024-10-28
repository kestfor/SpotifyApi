import asyncspotify


class TrackInQueue:

    def __init__(self, author_username: str, track_uri: str):
        self._author_username = author_username
        self._track_uri = track_uri

    @property
    def author_username(self):
        return self._author_username

    @property
    def track_uri(self):
        return self._track_uri


class TrackWithUser:

    def __init__(self, username: str, track: asyncspotify.SimpleTrack):
        self._username = username
        self._track = track

    @property
    def username(self):
        return self._username

    @property
    def track(self):
        return self._track