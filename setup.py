from setuptools import setup

setup(name='cmdstatic',
      version='0.1',
      py_modules=['static'],
      entry_points="""
      [dae.plugins]
      static=static:cmd_static
      """
      )
