# Standard library
import os
from pathlib import Path
from shutil import copytree
from tarfile import open as open_tar
from zipfile import ZipFile

# third-party
import build, pytest

try:
    from tomllib import load as load_toml # requires 3.11+
except ImportError: # 3.10 or earlier, so not in the standard library
    from tomli import load as load_toml # third-party implementation.

BBBB_ROOT = Path(__file__).parent.parent


def _toplevel_dotfiles(src, names):
    # a filter for copytree
    is_root = (Path(src) == BBBB_ROOT)
    return [n for n in names if n.startswith('.')] if is_root else []


def _read_config(filename, project_name, project_version):
    with open(filename, 'rb') as f:
        result = load_toml(f) # let errors propagate
    # Do template substitution and sorting.
    s = lambda t: t.format(name=project_name, version=project_version)
    result['sdist']['files'] = sorted(map(s, result['sdist']['files']))
    result['wheel']['files'] = sorted(map(s, result['wheel']['files']))
    result['wheel']['record'] = s(result['wheel']['record'])
    result['wheel']['sha256'] = sorted(map(s, result['wheel']['sha256']))
    result['wheel']['size'] = sorted(map(s, result['wheel']['size']))
    return result


@pytest.fixture
def setup(tmpdir):
    def _copy_project_and_get_metadata(project_path, config_rel_path):
        copytree(project_path, tmpdir, ignore=_toplevel_dotfiles, dirs_exist_ok=True)
        os.chdir(tmpdir)
        # Determine project name and version for use in tests.
        with open('pyproject.toml', 'rb') as f:
            project = load_toml(f)['project']
        name, version = project['name'], project['version']
        # Determine expectations for resulting sdist and wheel.
        toml_path = BBBB_ROOT / 'test' / config_rel_path / 'expected.toml'
        return _read_config(toml_path, name, version), name, version
    return _copy_project_and_get_metadata


def _list_tar_contents(name):
    with open_tar(name) as t:
        return sorted(m.path for m in t.getmembers())


def _list_zip_contents(name):
    with ZipFile(name) as z:
        return sorted(m.orig_filename for m in z.filelist)


def _read_manifest(name):
    with open(name) as f:
        entries = ['' if line.startswith('#') else line.rstrip() for line in f]
    return sorted(e for e in entries if e)


def _build(kind, src):
    build.ProjectBuilder(src).build(kind, 'test_dist')


def _verify_sdist(src_path, config_rel_path, expected, name, version):
    _build('sdist', src_path)
    actual = _list_tar_contents(f'test_dist/{name}-{version}.tar.gz')
    assert expected['sdist']['files'] == actual


def _verify_wheel(src_path, config_rel_path, expected, name, version):
    _build('wheel', src_path)
    actual = _list_zip_contents(f'test_dist/{name}-{version}-py3-none-any.whl')
    assert expected['wheel']['files'] == actual


def test_self_sdist(setup):
    expected, name, version = setup(BBBB_ROOT, '.')
    _verify_sdist('.', '.', expected, name, version)


def test_self_wheel(setup):
    expected, name, version = setup(BBBB_ROOT, '.')
    _verify_wheel('.', '.', expected, name, version)


def test_self_wheel_via_sdist(setup):
    expected, name, version = setup(BBBB_ROOT, '.')
    _build('sdist', '.')
    with open_tar(f'test_dist/{name}-{version}.tar.gz') as t:
        t.extractall(f'test_dist')
    _verify_wheel(f'test_dist/{name}-{version}', '.', expected, name, version)
