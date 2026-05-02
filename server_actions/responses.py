class APIError(Exception):
    def __init__(self, message):
        super().__init__(message)


class AnnotationResponse():
    def __init__(
        self,
        video_id: str,
        platform: str,
        title: str
    ):
        self.video_id = video_id
        self.platform = platform
        self.title = title
        

class SetReuploadResponse():
    def __init__(
        self,
        reupload_title: str,
        reupload_platform: str,
        original_title: str | None = None,
        original_platform: str | None = None
    ):
        self.reupload_title = reupload_title
        self.reupload_platform = reupload_platform
        self.original_title = original_title
        self.original_platform = original_platform
