from pathlib import Path
from typing import *

import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

    
def read_requirements(path: Union[str, Path]):
    with open(path, "r") as fh:
        return [line.strip() for line in fh.readlines() if not line.startswith("#")]


__VERSION__ = "0.1.10"

requirements = read_requirements("requirements.txt")

extras_require = {}
for path in Path("extras").rglob("*.txt"):
    extras_require[path.stem] = read_requirements(path)


setuptools.setup(
    name="mousse",
    packages=setuptools.find_packages(),
    version=__VERSION__,
    author="nghoangdat",
    author_email="18.hoang.dat.12@gmail.com",
    description="mousse",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/NgHoangDat/mousse.git",
    download_url=f"https://github.com/NgHoangDat/mousse/archive/v{__VERSION__}.tar.gz",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=requirements,
    extras_require=extras_require,
)
