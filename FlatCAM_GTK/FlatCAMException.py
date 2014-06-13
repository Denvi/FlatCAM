class FlatCAMException(Exception):
    def __init__(self, message="An error occurred", detail=""):
        self.message = message
        self.detail = detail

    def __str__(self):
        return "FlatCAM ERROR:", self.message