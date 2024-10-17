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

project = Path(__file__).parent.parent


def _toplevel_dotfiles(src, names):
    # a filter for copytree
    is_root = (Path(src) == project)
    return [n for n in names if n.startswith('.')] if is_root else []


@pytest.fixture
def copy_self(tmpdir):
    copytree(project, tmpdir, ignore=_toplevel_dotfiles, dirs_exist_ok=True)
    os.chdir(tmpdir)


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


def test_self_sdist(copy_self):
    build.ProjectBuilder('.').build('sdist', 'test_dist')
    expected = _read_config(project / 'test' / 'expected.toml', 'bbbb', '0.3.0')
    actual = _list_tar_contents(f'test_dist/bbbb-0.3.0.tar.gz')
    assert expected['sdist']['files'] == actual


def test_self_wheel(copy_self):
    build.ProjectBuilder('.').build('wheel', 'test_dist')
    expected = _read_config(project / 'test' / 'expected.toml', 'bbbb', '0.3.0')
    actual = _list_zip_contents('test_dist/bbbb-0.3.0-py3-none-any.whl')
    assert expected['wheel']['files'] == actual


def test_self_wheel_via_sdist(copy_self):
    build.ProjectBuilder('.').build('sdist', 'test_dist')
    name = 'bbbb-0.3.0'
    with open_tar(f'test_dist/{name}.tar.gz') as t:
        t.extractall(f'test_dist')
    build.ProjectBuilder(f'test_dist/{name}').build('wheel', 'test_dist')
    expected = _read_config(project / 'test' / 'expected.toml', 'bbbb', '0.3.0')
    actual = _list_zip_contents('test_dist/bbbb-0.3.0-py3-none-any.whl')
    assert expected['wheel']['files'] == actual
