try:
    from setuptools import setup
    kw = {
        'entry_points': {
            'console_scripts': [
                'staticpy = static:main',
            ],
        },
        'zip_safe': False,
    }
except ImportError:
    from distutils.core import setup
    kw = {'scripts': ['static.py']}

setup(
    name='staticpy',
    version='0.2',
    url='https://github.com/MOON-CLJ/staticpy',
    license='BSD',
    author='CLJ',
    author_email='lijunli2598@gmail.com',
    description='dae is a static file manager(not rely on dae)',
    py_modules=['static'],
    install_requires=[
        'clint',
    ],
    **kw
)
