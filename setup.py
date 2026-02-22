#!/usr/bin/env python3
"""Setup script for CronPilot."""

from setuptools import setup, find_packages

setup(
    name="cronpilot",
    version="1.0.0",
    description="Cron Expression Parser, Builder & Scheduler - Zero Dependencies",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="ATLAS (Team Brain)",
    author_email="metaphyllc@example.com",
    url="https://github.com/DonkRonk17/CronPilot",
    py_modules=["cronpilot"],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "cronpilot=cronpilot:main",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
    ],
    keywords="cron, crontab, scheduler, parser, builder, time, automation",
    license="MIT",
)
