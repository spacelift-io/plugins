"""
Setup script for spaceforge - Spacelift Plugin Framework
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="spaceforge",
    author="Spacelift",
    author_email="support@spacelift.io",
    description="A Python framework for building Spacelift plugins",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/spacelift-io/plugins",
    project_urls={
        "Bug Reports": "https://github.com/spacelift-io/plugins/issues",
        "Source": "https://github.com/spacelift-io/plugins",
    },
    packages=find_packages(),
    package_data={
        "spaceforge": ["schema.json"],
    },
    include_package_data=True,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Systems Administration",
    ],
    python_requires=">=3.9",
    install_requires=[
        "PyYAML>=6.0",
        "click>=8.0.0",
        "pydantic>=2.11.7",
        "Jinja2>=3.1.0",
        "mergedeep>=1.3.4",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov",
            "black",
            "isort",
            "mypy",
            "autoflake"
        ],
    },
    entry_points={
        "console_scripts": [
            "spaceforge=spaceforge.__main__:main",
        ],
    },
    keywords="spacelift plugin framework infrastructure devops spaceforge",
    zip_safe=False,
)