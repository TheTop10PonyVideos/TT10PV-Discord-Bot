class APIError(Exception):
    def __init__(self, message):
        super().__init__(message)


class AnnotationResponse():
    def __init__(
        self,
        platform: str,
        title: str
    ):
        self.title = title
        self.platform = platform
        

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


# TODO
class ValidationResponse():
    def __init__(
            self
        ):
        pass