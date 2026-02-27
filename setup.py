from setuptools import setup, find_packages

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="logfix",
    version="1.0.0",
    description="LogFix Python SDK — 에러 추적 SDK",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="LogFix Team",
    url="https://github.com/logfix/logfix-python",
    packages=find_packages(exclude=["tests*"]),
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.20.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov",
        ],
        "flask": ["flask>=2.0"],
        "django": ["django>=3.2"],
        "fastapi": ["fastapi>=0.95", "starlette>=0.27"],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries",
        "Topic :: System :: Logging",
    ],
    keywords="error tracking logging monitoring sdk",
)
