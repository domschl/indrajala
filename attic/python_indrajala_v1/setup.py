import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="indrajala",
    version="0.0.1",
    author="Dominik Schlösser",
    author_email="dsc@dosc.net",
    description="indrajala tools in python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/domschl/indrajala",
    project_urls={
        "Bug Tracker": "https://github.com/domschl/indrajala/issues"
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.8",
    )
