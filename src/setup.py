from setuptools import setup, find_packages

setup(
    name="referencing",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "requests>=2.25.0",
        "python-docx>=0.8.11",
        "aiohttp>=3.8.0",
        "flask>=2.0.0",
        "python-dotenv>=0.19.0",
    ],
)
