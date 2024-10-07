import build
import os
from pathlib import Path
import pytest
from shutil import copytree
from tarfile import open as open_tar


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
        expected = [f'{root_name}/{e}' for e in entries if e]
        expected.append(root_name)
        expected.sort()
    with open_tar(f'test_dist/{root_name}.tar.gz') as t:
        actual = sorted(m.path for m in t.getmembers())
    assert expected == actual


def test_self_sdist(copy_self):
    tmpdir = copy_self()
    os.chdir(tmpdir)
    build.ProjectBuilder('.').build('sdist', 'test_dist')
    assert 'test_dist' in os.listdir()
    _verify_sdist('bbbb-0.3.0', project / 'test' / 'self_manifest.txt')
