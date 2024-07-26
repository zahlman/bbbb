from os import walk # Path doesn't have .walk until 3.12
from pathlib import Path
import tarfile
from zipfile import ZipFile, ZIP_DEFLATED


SDIST_NAME = "bbbb-0.1.0"
SDIST_FILENAME = SDIST_NAME + ".tar.gz"
WHEEL_FILENAME = "bbbb-0.1.0-py3-none-any.whl"


def _exclude_hidden_and_special_files(archive_entry):
    # Tarfile filter to exclude hidden and special files from the archive
    if archive_entry.isfile() or archive_entry.isdir():
        if not Path(archive_entry.name).name.startswith("."):
            return archive_entry


def _make_sdist(sdist_dir):
    # Make an sdist and return both the Python object and its filename
    sdist_path = Path(sdist_dir) / SDIST_FILENAME
    sdist = tarfile.open(sdist_path, "w:gz", format=tarfile.PAX_FORMAT)
    # Tar up the whole directory, minus hidden and special files
    sdist.add(
        Path('.').resolve(), arcname=SDIST_NAME,
        filter=_exclude_hidden_and_special_files
    )
    return sdist, SDIST_FILENAME


def build_sdist(sdist_dir, config_settings):
    """PEP 517 sdist creation hook"""
    sdist, sdist_filename = _make_sdist(sdist_dir)
    return sdist_filename


def build_wheel(
    wheel_directory, metadata_directory=None, config_settings=None
):
    """PEP 517 wheel creation hook"""
    wheel_path = Path(wheel_directory) / WHEEL_FILENAME
    # Assume src layout and that metadata has already been created therein.
    to_include = Path('src')
    # shutil.make_archive would suffice, but in the long run we'll
    # want custom features: sorting to put the `.dist-info` folder at
    # the end of the archive, and the ability to override timestamps.
    with ZipFile(wheel_path, 'w', compression=ZIP_DEFLATED) as wheel:
        for path, folders, files in walk(to_include):
            path = Path(path)
            for file in files:
                path /= file
                wheel.write(path, arcname=path.relative_to(to_include))
    return WHEEL_FILENAME
