"""Setup script for the reference manager package."""
from setuptools import setup, find_packages

setup(
    name="reference_manager",
    version="1.0.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "requests>=2.25.0",
        "python-docx>=0.8.11",
        "aiohttp>=3.8.0",
        "flask>=2.0.0",
        "python-dotenv>=0.19.0",
    ],
    python_requires=">=3.8",
    author="Stenford Ruvinga",
    author_email="stenford41@hotmail.com",
    description="A tool for managing academic references and citations",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    keywords="reference citation academic bibliography",
    include_package_data=True,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Text Processing :: Markup",
    ],
)