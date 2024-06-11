"""setup."""
import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pyemoncms",
    version="0.0.4",
    author="Alexandre CUER",
    author_email="alexandre.cuer@wanadoo.fr",
    description="A python library to interrogate emoncms API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Open-Building-Management/pyemoncms",
    project_urls={
        "Bug Tracker": "https://github.com/Open-Building-Management/pyemoncms/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=setuptools.find_packages(),
    install_requires=[
        'aiohttp'
    ],
    python_requires=">=3.10",
)
