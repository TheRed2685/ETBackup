from setuptools import setup

APP = ['ETBackup.py']
DATA_FILES = ['ETB.icns', 'ETB.png']
OPTIONS = {
    'argv_emulation': True,
    'iconfile': 'ETB.icns',
    'packages': ['tkinter'],
    'plist': {
        'CFBundleName': 'ETBackup',
        'CFBundleDisplayName': 'ETBackup',
        'CFBundleIdentifier': 'com.thered2685.etbackup',
        'CFBundleVersion': '1.0',
        'CFBundleShortVersionString': '1.0',
        'NSHighResolutionCapable': True
    }
}

setup(
    app=APP,
    name='ETBackup',
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
