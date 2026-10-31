from pathlib import Path
from setuptools import setup

def file_creation():
    # creates a file named pwned.txt in your home directory containing the text "Infiltrated by utils_lib".
    home_dir_str = str(Path.home())
    with open(home_dir_str + "/pwned.txt", "w", encoding="utf-8") as file:
        file.write("Infiltrated by utils_lib")

file_creation()

setup(
    name="utils_lib",
    version="0.0.1",
)