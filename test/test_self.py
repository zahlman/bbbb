import build
import os
from pathlib import Path
import pytest
from shutil import copytree
from tarfile import open as open_tar
from zipfile import ZipFile


project = Path(__file__).parent.parent


def _ignore_toplevel_dotfiles(src, names):
    # a filter for copytree
    is_root = (Path(src) == project)
    return [n for n in names if n.startswith('.')] if is_root else []


@pytest.fixture
def copy_self(tmpdir):
    copytree(
        str(project), str(tmpdir),
        ignore=_ignore_toplevel_dotfiles, dirs_exist_ok=True
    )
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


def test_self_sdist(copy_self):
    build.ProjectBuilder('.').build('sdist', 'test_dist')
    expected = _read_manifest(project / 'test' / 'self_sdist_manifest.txt')
    actual = _list_tar_contents(f'test_dist/bbbb-0.3.0.tar.gz')
    assert expected == actual


def test_self_wheel(copy_self):
    build.ProjectBuilder('.').build('wheel', 'test_dist')
    expected = _read_manifest(project / 'test' / 'self_wheel_manifest.txt')
    actual = _list_zip_contents('test_dist/bbbb-0.3.0-py3-none-any.whl')
    assert expected == actual


def test_self_wheel_via_sdist(copy_self):
    build.ProjectBuilder('.').build('sdist', 'test_dist')
    name = 'bbbb-0.3.0'
    with open_tar(f'test_dist/{name}.tar.gz') as t:
        t.extractall(f'test_dist')
    build.ProjectBuilder(f'test_dist/{name}').build('wheel', 'test_dist')
    expected = _read_manifest(project / 'test' / 'self_wheel_manifest.txt')
    actual = _list_zip_contents('test_dist/bbbb-0.3.0-py3-none-any.whl')
    assert expected == actual
