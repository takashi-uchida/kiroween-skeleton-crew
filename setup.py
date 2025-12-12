"""NecroCode setup configuration"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="necrocode",
    version="0.1.0",
    author="NecroCode Team",
    description="Kiroネイティブ並列実行フレームワーク",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/takashi-uchida/kiroween-skeleton-crew",
    packages=find_packages(exclude=["tests", "examples", "worktrees"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    install_requires=[
        "click>=8.0.0",
        "pyyaml>=6.0.0",
        "gitpython>=3.1.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "necrocode=necrocode.cli:cli",
        ],
    },
)
