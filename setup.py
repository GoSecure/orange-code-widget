from setuptools import setup

setup(name="Code Viewer",
      packages=["orangecode"],
      package_data={"orangecode": ["icons/*.svg"]},
      classifiers=["Example :: Invalid"],
      entry_points={"orange.widgets": "Code = orangecode"},
      )
