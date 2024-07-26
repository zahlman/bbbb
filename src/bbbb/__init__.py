from io import BytesIO
from os import walk # Path doesn't have .walk until 3.12
from pathlib import Path
from tarfile import open as TarFile, PAX_FORMAT, TarInfo
from zipfile import ZipFile, ZIP_DEFLATED


NAME = 'bbbb'
VERSION = '0.1.0'
PYTHON_TAG = 'py3'
ABI_TAG = 'none'
PLATFORM_TAG = 'any'
# According to the specifications on packaging.python.org, for a
# pyproject.toml-based sdist, we must conform to version 2.2 or later.
# So we will specify version 2.2 even though we are only using basic features.
METADATA = f'Metadata-Version: 2.2\nName: {NAME}\nVersion: {VERSION}'
WHEEL = f'Wheel-Version: 1.0\nGenerator: bbbb 0.1.0\nRoot-Is-Purelib: true\nTag: {PYTHON_TAG}-{ABI_TAG}-{PLATFORM_TAG}'
# Also need a RECORD file and to copy LICENSE into the .dist-info.
# Also should support making entry_points.txt.


def _exclude_hidden_and_special_files(archive_entry):
    # Tarfile filter to exclude hidden and special files from the archive
    if archive_entry.isfile() or archive_entry.isdir():
        if not Path(archive_entry.name).name.startswith("."):
            return archive_entry


def build_sdist(sdist_directory, config_settings):
    # Make an sdist and return both the Python object and its filename
    name = f"{NAME}-{VERSION}.tar.gz"
    sdist_path = Path(sdist_directory) / name
    with TarFile(sdist_path, "w:gz", format=PAX_FORMAT) as sdist:
        # Tar up the whole directory, minus hidden and special files
        sdist.add(
            Path('.').resolve(), arcname=f'{NAME}-{VERSION}',
            filter=_exclude_hidden_and_special_files
        )
        # Create (or overwrite) metadata file (directly into archive).
        info = TarInfo(f'{NAME}-{VERSION}/PKG-INFO')
        data = METADATA.encode()
        info.size = len(data)
        sdist.addfile(info, BytesIO(data))
    return name


def build_wheel(
    # This is the order specified in PEP 517, subsection "Mandatory hooks".
    # The example build backend in Appendix A reverses the order of
    # `config_settings` and `metadata_directory`. However, this does not
    # actually work with standard tooling, because `pyproject_hooks` passes
    # these arguments positionally and in this specific order.
    wheel_directory, config_settings=None, metadata_directory=None
):
    wheel_name = f'{NAME}-{VERSION}-{PYTHON_TAG}-{ABI_TAG}-{PLATFORM_TAG}.whl'
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
        # Generate the .dist-info folder.
        di = Path(f'{NAME}-{VERSION}.dist-info')
        wheel.writestr(str(di / 'METADATA'), METADATA)
        wheel.writestr(str(di / 'WHEEL'), WHEEL)
        # TODO: RECORD, entry_points.txt
        wheel.write('LICENSE', arcname=di / 'LICENSE')
    return wheel_name
