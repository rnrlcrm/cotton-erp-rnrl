"""Setup file for Commodity ERP Backend."""
from setuptools import setup, find_packages

setup(
    name="commodity-erp-backend",
    version="0.1.0",
    description="Commodity ERP Backend API",
    packages=find_packages(exclude=["tests*"]),
    python_requires=">=3.11",
    install_requires=[
        # Dependencies are managed in requirements.txt
    ],
)
