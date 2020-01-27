class Image:
    # This is only a data class like the Place class. A Place can have
    # multiple Images. This creates and structure which makes code more
    # readable when having to deal with the processing of all the files
    def __init__(self, path):
        self.path = path
        self.base_name = ""
        self.metadata_file = ""
