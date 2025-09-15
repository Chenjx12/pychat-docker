from setuptools import setup, find_packages

setup(
    name="pychat",
    version="0.1.0",
    packages=find_packages(),   # 自动发现 app 包
    python_requires=">=3.11",
)