import os
from setuptools import setup

requires = [
        'twilio',
        'pyyaml',
        'shove',
        'flask',
        'requests',
        'sqlalchemy',
        'BeautifulSoup4',
        'jinja2',
        'pastescript'
        ]

if os.environ.get('OPENSHIFT_REPO_DIR'):
    requires.append('mysql-python')

setup(
        name="catfacts",
        version="0.1.0",
        author="Ross Delinger",
        author_email="rdelinger@helixoide.com",
        install_requires=requires,
        packages=['catfacts'],
        entry_points="""
        [console_scripts]
        catfacts = catfacts:main
        [paste.app_factory]
        main = catfacts:create
        """,
        zip_safe=False,
        )
