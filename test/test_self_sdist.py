import build
import os
from pathlib import Path
import pytest
from shutil import copytree
from tarfile import open as open_tar
from zipfile import ZipFile


project = Path(__file__).parent.parent


@pytest.fixture
def copy_self(tmpdir):
    def copy():
        copytree(str(project), str(tmpdir), dirs_exist_ok=True)
        return tmpdir
    return copy


def _process_line(line):
    return '' if line.startswith('#') else line.rstrip()


def _verify_sdist(root_name, manifest_file):
    with open(manifest_file) as f:
        entries = map(_process_line, f)
        expected = [e for e in entries if e]
        expected.sort()
    with open_tar(f'test_dist/{root_name}.tar.gz') as t:
        actual = sorted(m.path for m in t.getmembers())
    assert expected == actual


def test_self_sdist(copy_self):
    tmpdir = copy_self()
    os.chdir(tmpdir)
    build.ProjectBuilder('.').build('sdist', 'test_dist')
    _verify_sdist('bbbb-0.3.0', project / 'test' / 'self_sdist_manifest.txt')


def _verify_wheel(root_name, manifest_file):
    with open(manifest_file) as f:
        entries = map(_process_line, f)
        expected = [e for e in entries if e]
        expected.sort()
    with ZipFile(f'test_dist/{root_name}-py3-none-any.whl') as z:
        actual = sorted(m.orig_filename for m in z.filelist)
    assert expected == actual


def test_self_wheel(copy_self):
    tmpdir = copy_self()
    os.chdir(tmpdir)
    build.ProjectBuilder('.').build('wheel', 'test_dist')
    _verify_wheel('bbbb-0.3.0', project / 'test' / 'self_wheel_manifest.txt')


def test_self_wheel_via_sdist(copy_self):
    tmpdir = copy_self()
    os.chdir(tmpdir)
    build.ProjectBuilder('.').build('sdist', 'test_dist')
    name = 'bbbb-0.3.0'
    with open_tar(f'test_dist/{name}.tar.gz') as t:
        t.extractall(f'test_dist')
    build.ProjectBuilder(f'test_dist/{name}').build('wheel', 'test_dist')
    _verify_wheel('bbbb-0.3.0', project / 'test' / 'self_wheel_manifest.txt')
