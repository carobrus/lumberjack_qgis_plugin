class Place:
    # This is only a data class like the Image class. A Place can have
    # multiple Images. This creates and structure which makes code more
    # readable when having to deal with the processing of all the files
    def __init__(self, directory_path):
        self.directory_path = directory_path
        self.extension_file_path = ""
        self.vector_file_path = ""
        self.dem_textures_file_path = ""
        self.mask = ""
        self.images = []
