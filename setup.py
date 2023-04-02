from setuptools import setup, find_packages

setup(
    name = "ImageTagger",
    version = "1.0",
    description = "Tags .jpeg images",
    packages = find_packages(),
    install_requires = ['flask','flask_session','wtforms','PIL/Image','PIL/ExifTags/TAGS']
)