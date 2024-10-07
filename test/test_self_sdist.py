import os
from pathlib import Path
import pytest
from shutil import copytree
from tarfile import open as open_tar


project = Path(__file__).parent.parent
# Since the project doesn't handle editable wheels yet, it can't install
# itself in editable mode for testing. To ensure we test the in-progress
# code (without having to uninstall/build/reinstall manually), we hack
# sys.path.
import sys
sys.path.insert(0, str(project / 'src'))
print(sys.path)
import bbbb


@pytest.fixture
def copy_self(tmpdir):
    def copy():
        copytree(str(project), str(tmpdir), dirs_exist_ok=True)
        return tmpdir
    return copy


def _verify_sdist(root_name, manifest_file):
    with open(manifest_file) as f:
        expected = [root_name] + [f'{root_name}/{e.strip()}' for e in f]
    with open_tar(f'test_sdist/{root_name}.tar.gz') as t:
        actual = sorted(m.path for m in t.getmembers())
    assert expected == actual


def test_self_sdist(copy_self):
    tmpdir = copy_self()
    os.chdir(tmpdir)
    bbbb.build_sdist('test_sdist')
    assert 'test_sdist' in os.listdir()
    _verify_sdist('bbbb-0.3.0', project / 'test' / 'self_manifest.txt')
