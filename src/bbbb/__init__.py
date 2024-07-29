from importlib import import_module
from io import BytesIO
from pathlib import Path
import sys
from tarfile import open as TarFile, TarInfo
# Build hooks
from .wheel import build_wheel, get_requires_for_build_wheel
# Private implementation stuff
from .wheel import _get_config, _metadata_file, _prepare_lines


def _invoke(name, *args, **kwargs):
    module_name, colon, func_name = name.partition(':')
    module = import_module(module_name)
    func = getattr(module, func_name)
    return func(*args, **kwargs)


_always_include = set(map(str.casefold, ('COPYING', 'LICENSE', 'README')))
def _allow_path(config, path):
    # Include certain files regardless of user setting.
    if (path.parent == Path('.')):
        if path.stem.casefold() in _always_include:
            return True
        if path.name.casefold() == 'pyproject.toml'.casefold():
            return True
    # Without a hook, just exclude dotfiles.
    if 'file_filter' in config['sdist']:
        return _invoke(config['sdist']['file_filter'], config, path)
    else:
        return not path.name.startswith('.')


def _filter_sdist(config, root_folder, tar_info):
    if not (tar_info.isfile() or tar_info.isdir()):
        return None
    path = Path(tar_info.name).relative_to(root_folder)
    return tar_info if _allow_path(config, path) else None


def get_requires_for_build_sdist(config_settings=None):
    return ['tomli;python_version<"3.11"']


def build_sdist(sdist_directory, config_settings=None):
    config = _get_config(config_settings)
    name, version = config['name'], config['version']
    # Make an sdist and return both the Python object and its filename
    result_name = f'{name}-{version}.tar.gz'
    sdist_path = Path(sdist_directory) / result_name
    # TODO: use a proper dynamic import
    sys.path.append(str(Path('.').resolve()))
    with TarFile(sdist_path, 'w:gz') as sdist:
        root_folder = f'{name}-{version}'
        filter = lambda tar_info: _filter_sdist(config, root_folder, tar_info)
        # Tar up the whole directory, minus hidden and special files
        sdist.add(Path('.').resolve(), arcname=root_folder, filter=filter)
        # Create (or overwrite) metadata file (directly into archive).
        info = TarInfo(f'{root_folder}/PKG-INFO')
        data = _prepare_lines(_metadata_file(config))
        info.size = len(data)
        sdist.addfile(info, BytesIO(data))
    return result_name
