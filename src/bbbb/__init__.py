from os import walk # Path doesn't have .walk until 3.12
from pathlib import Path
import tarfile
from zipfile import ZipFile, ZIP_DEFLATED


NAME = 'bbbb'
VERSION = '0.1.0'
PYTHON_TAG = 'py3'
ABI_TAG = 'none'
PLATFORM_TAG = 'any'


def _exclude_hidden_and_special_files(archive_entry):
    # Tarfile filter to exclude hidden and special files from the archive
    if archive_entry.isfile() or archive_entry.isdir():
        if not Path(archive_entry.name).name.startswith("."):
            return archive_entry


def build_sdist(sdist_directory, config_settings):
    # Make an sdist and return both the Python object and its filename
    name = f"{NAME}-{VERSION}.tar.gz"
    sdist_path = Path(sdist_directory) / name
    sdist = tarfile.open(sdist_path, "w:gz", format=tarfile.PAX_FORMAT)
    # Tar up the whole directory, minus hidden and special files
    sdist.add(
        Path('.').resolve(), arcname=f'{NAME}-{VERSION}',
        filter=_exclude_hidden_and_special_files
    )
    return name


def build_wheel(
    # This is the order specified in PEP 517, subsection "Mandatory hooks".
    # The example build backend in Appendix A reverses the order of
    # `config_settings` and `metadata_directory`. However, this does not
    # actually work with standard tooling, because `pyproject_hooks` passes
    # these arguments positionally and in this specific order.
    wheel_directory, config_settings=None, metadata_directory=None
):
    wheel_name = f"{NAME}-{VERSION}-{PYTHON_TAG}-{ABI_TAG}-{PLATFORM_TAG}.whl"
    wheel_path = Path(wheel_directory) / wheel_name
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
    return wheel_name
