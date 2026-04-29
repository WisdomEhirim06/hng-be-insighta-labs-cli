from setuptools import setup, find_packages

setup(
    name="insighta",
    version="1.0.0",
    py_modules=["main", "api_client", "auth_helper"],
    install_requires=[
        "typer[all]",
        "click==8.1.7",
        "rich",
        "httpx",
        "python-dotenv",
    ],
    entry_points={
        "console_scripts": [
            "insighta=main:app",
        ],
    },
)
