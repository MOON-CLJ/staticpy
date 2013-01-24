from setuptools import setup
kw = {
    'entry_points': {
        'console_scripts': [
            'staticpy = static.core:main',
        ],
    },
    'zip_safe': False,
}

setup(
    name='staticpy',
    version='0.2',
    url='https://github.com/MOON-CLJ/staticpy',
    license='BSD',
    author='CLJ',
    author_email='lijunli2598@gmail.com',
    description='staticpy is a static file manager',
    py_modules=['static.core', 'static.utils'],
    install_requires=[
        'clint',
    ],
    dependency_links=[
        'https://github.com/MOON-CLJ/clint/tarball/develop#egg=clint',
    ],
    **kw
)
