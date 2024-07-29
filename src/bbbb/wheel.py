from base64 import urlsafe_b64encode
from hashlib import sha256
from itertools import product as cartesian_product
from os import walk # Path.walk requires 3.12; simpler to ignore it
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


BBBB_VERSION = '0.3.0'
# TODO: generate a version label in the self-build process?


# From PEP 517:
# Some backends may have extra requirements for creating sdists, such as
# version control tools. However, some frontends may prefer to make
# intermediate sdists when producing wheels, to ensure consistency. If the
# backend cannot produce an sdist because a dependency is missing, or for
# another well understood reason, it should raise an exception of a specific
# type which it makes available as UnsupportedOperation on the backend object.

# When this file is used directly as a backend (via a specially crafted wheel
# that contains only this module), that should only be because it's been
# installed and invoked by an installer (such as Pip) for the express purpose
# of creating a wheel from an sdist (of some other project) from PyPI.
# In these circumstances, something has gone wrong if any attempt is made
# at all to build an sdist.

# The "main" code implements a build_sdist hook and only uses this file
# for wheel-specific functionality.
class UnsupportedOperation(Exception):
    pass


def build_sdist(sdist_directory, config_settings=None):
    raise UnsupportedOperation


def _metadata_file(config):
    # According to the specifications on packaging.python.org, for a
    # pyproject.toml-based sdist, we must conform to version 2.2 or later.
    # So we specify version 2.2 even though we are only using basic features.
    name, version = config['name'], config['version']
    return ['Metadata-Version: 2.2', f'Name: {name}', f'Version: {version}']


def _wheel_file(config):
    generator = f'Generator: bbbb {BBBB_VERSION}'
    info = ['Wheel-Version: 1.0', generator, 'Root-Is-Purelib: true']
    tag_groups = cartesian_product(*(t.split('.') for t in config['tags']))
    return info + [f'Tag: {"-".join(tags)}' for tags in tag_groups]


def _to_base64_for_record(data):
    return urlsafe_b64encode(data).decode('ascii').rstrip('=')


def _sha256_digest(f):
    hasher = sha256()
    # Somewhat arbitrary page size.
    # Avoid reading entire files into memory simultaneously
    # (although it shouldn't normally cause a problem).
    for chunk in iter(lambda: f.read(4096), b''):
        hasher.update(chunk)
    return hasher.digest()


def _add_file(wheel, records, dst_path, src_path):
    wheel.write(src_path, arcname=dst_path)
    size = src_path.stat().st_size
    with open(src_path, 'rb') as f:
        checksum = _to_base64_for_record(_sha256_digest(f))
    records.append(f'{dst_path},sha256={checksum},{size}')


def _prepare_lines(lines):
    return ('\n'.join(lines) + '\n').encode('utf-8', 'strict')


def _add_text(wheel, records, dst_path, lines):
    data = _prepare_lines(lines)
    wheel.writestr(str(dst_path), data)
    size = len(data)
    checksum = _to_base64_for_record(sha256(data).digest())
    records.append(f'{dst_path},sha256={checksum},{size}')


def _add_folder(wheel, records, dst_prefix, src_prefix):
    for path, folders, files in walk(src_prefix):
        path = Path(path)
        for file in files:
            src = path / file
            dst = dst_prefix / src.relative_to(src_prefix)
            _add_file(wheel, records, dst, src)


def _add_other_dist_info_files(add, config):
    add('METADATA', _metadata_file(config))
    add('WHEEL', _wheel_file(config))
    # TODO: entry_points.txt
    for license_path in Path('.').iterdir():
        if license_path.stem.casefold() == 'LICENSE'.casefold():
            add(str(license_path), license_path)


def _add_dist_info(wheel, records, config):
    name, version = config['name'], config['version']
    di = Path(f'{name}-{version}.dist-info')
    def add_dist_file(name, lines):
        handler = _add_file if isinstance(lines, Path) else _add_text
        handler(wheel, records, di / name, lines)
    _add_other_dist_info_files(add_dist_file, config)
    # add self-reference before writing the file, but after all others.
    records.append(f'{di / "RECORD"},,')
    add_dist_file('RECORD', records)


def _read_toml(name):
    # Can't import at the start, because of the need to bootstrap the
    # environment via `get_requires_for_build_*`.
    try:
        from tomllib import load as load_toml # requires 3.11+
    except ImportError: # 3.10 or earlier, so not in the standard library
        from tomli import load as load_toml # third-party implementation.
    with open(name, 'rb') as f:
        return load_toml(f) # let errors propagate


def _get_config(manual):
    # Also used for sdists, but the goal is to make a single-file
    # backend option for installers to build wheels - so the code
    # is left here, and imported from the main file.
    # It's also not part of the public interface.
    ppt = _read_toml('pyproject.toml')
    project = ppt['project']
    bbbb = ppt.get('tool', {}).get('bbbb', {})
    python_tag = manual.get('python_tag', 'py3')
    abi_tag = manual.get('abi_tag', 'none')
    platform_tag = manual.get('platform_tag', 'any')
    return {
        'name': project['name'],
        'version': project['version'],
        'tags': (python_tag, abi_tag, platform_tag),
        'sdist': bbbb.get('sdist', {}),
        'wheel': bbbb.get('wheel', {})
    }


def get_requires_for_build_wheel(config_settings=None):
    return ['tomli;python_version<"3.11"']


def build_wheel(
    # This is the order specified in PEP 517, subsection 'Mandatory hooks'.
    # The example build backend in Appendix A reverses the order of
    # `config_settings` and `metadata_directory`. However, this does not
    # actually work with standard tooling, because `pyproject_hooks` passes
    # these arguments positionally and in this specific order.
    wheel_directory, config_settings=None, metadata_directory=None
):
    config = _get_config(config_settings)
    name, version, tags = config['name'], config['version'], config['tags']
    wheel_name = f'{name}-{version}-{"-".join(tags)}.whl'
    wheel_path = Path(wheel_directory) / wheel_name
    records = []
    with ZipFile(wheel_path, 'w', compression=ZIP_DEFLATED) as wheel:
        _add_folder(wheel, records, Path('.'), Path('src'))
        _add_dist_info(wheel, records, config)
    return wheel_name
