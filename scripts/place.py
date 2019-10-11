class Place:

    def __init__(self, directory_path):
        self.directory_path = directory_path
        self.extension_file_path = ""
        self.vector_file_path = ""
        self.dem_textures_file_path = ""
        self.mask = ""
        self.images = []
