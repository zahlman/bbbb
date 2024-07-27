from base64 import urlsafe_b64encode
from hashlib import sha256
from io import BytesIO
from os import walk # Path.walk requires 3.12; simpler to ignore it
from pathlib import Path
from tarfile import open as TarFile, PAX_FORMAT, TarInfo
from zipfile import ZipFile, ZIP_DEFLATED


def _get_config():
    # Can't import at the start, because of the need to bootstrap the
    # environment via `get_requires_for_build_*`.
    try:
        from tomllib import load as load_toml # requires 3.11+
    except ImportError: # 3.10 or earlier, so not in the standard library
        from tomli import load as load_toml # third-party implementation.
    # No validation is attempted; that's the job of a frontend or integrator.
    with open('pyproject.toml', 'rb') as f:
        return load_toml(f) # let errors propagate


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


def get_requires_for_build_sdist(config_settings=None):
    return ['tomli;python_version<"3.11"']


def _exclude_hidden_and_special_files(archive_entry):
    # Tarfile filter to exclude hidden and special files from the archive
    if archive_entry.isfile() or archive_entry.isdir():
        if not Path(archive_entry.name).name.startswith('.'):
            return archive_entry


def build_sdist(sdist_directory, config_settings=None):
    _get_config()
    # Make an sdist and return both the Python object and its filename
    name = f'{NAME}-{VERSION}.tar.gz'
    sdist_path = Path(sdist_directory) / name
    with TarFile(sdist_path, 'w:gz', format=PAX_FORMAT) as sdist:
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


def _add_file_to_wheel(wheel, records, dst_path, src_path):
    wheel.write(src_path, arcname=dst_path)
    size = src_path.stat().st_size
    with open(src_path, 'rb') as f:
        checksum = _to_base64_for_record(_sha256_digest(f))
    records.append(f'{dst_path},sha256={checksum},{size}\n')


def _add_text_to_wheel(wheel, records, dst_path, text):
    data = text.encode('utf-8', 'strict')
    wheel.writestr(str(dst_path), data)
    size = len(data)
    checksum = _to_base64_for_record(sha256(data).digest())
    records.append(f'{dst_path},sha256={checksum},{size}\n')


def _add_folder_to_wheel(wheel, records, dst_prefix, src_prefix):
    for path, folders, files in walk(src_prefix):
        path = Path(path)
        for file in files:
            src = path / file
            dst = dst_prefix / src.relative_to(src_prefix)
            _add_file_to_wheel(wheel, records, dst, src)


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
    _get_config()
    wheel_name = f'{NAME}-{VERSION}-{PYTHON_TAG}-{ABI_TAG}-{PLATFORM_TAG}.whl'
    wheel_path = Path(wheel_directory) / wheel_name
    records = []
    with ZipFile(wheel_path, 'w', compression=ZIP_DEFLATED) as wheel:
        _add_folder_to_wheel(wheel, records, Path('.'), Path('src'))
        # Generate the .dist-info folder.
        di = Path(f'{NAME}-{VERSION}.dist-info')
        _add_text_to_wheel(wheel, records, di / 'METADATA', METADATA)
        _add_text_to_wheel(wheel, records, di / 'WHEEL', WHEEL)
        # TODO: entry_points.txt
        _add_file_to_wheel(wheel, records, di / 'LICENSE', Path('LICENSE'))
        record_path = di / 'RECORD'
        records.append(f'{record_path},,')
        _add_text_to_wheel(wheel, records, record_path, ''.join(records))
    return wheel_name
