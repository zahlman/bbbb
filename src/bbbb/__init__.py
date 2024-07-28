from io import BytesIO
from pathlib import Path
from tarfile import open as TarFile, TarInfo
# Build hooks
from .wheel import build_wheel, get_requires_for_build_wheel
# Private implementation stuff
from .wheel import _get_config, _metadata_file, _prepare_lines


def _exclude_hidden_and_special_files(archive_entry):
    # Tarfile filter to exclude hidden and special files from the archive
    if archive_entry.isfile() or archive_entry.isdir():
        if not Path(archive_entry.name).name.startswith('.'):
            return archive_entry


def get_requires_for_build_sdist(config_settings=None):
    return ['tomli;python_version<"3.11"']


def build_sdist(sdist_directory, config_settings=None):
    config = _get_config(config_settings)
    name, version = config['name'], config['version']
    # Make an sdist and return both the Python object and its filename
    result_name = f'{name}-{version}.tar.gz'
    sdist_path = Path(sdist_directory) / result_name
    with TarFile(sdist_path, 'w:gz') as sdist:
        # Tar up the whole directory, minus hidden and special files
        sdist.add(
            Path('.').resolve(), arcname=f'{name}-{version}',
            filter=_exclude_hidden_and_special_files
        )
        # Create (or overwrite) metadata file (directly into archive).
        info = TarInfo(f'{name}-{version}/PKG-INFO')
        data = _prepare_lines(_metadata_file(config))
        info.size = len(data)
        sdist.addfile(info, BytesIO(data))
    return result_name
