import os
from pathlib import Path
import pytest
from shutil import copytree


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


def test_self_sdist(copy_self):
    tmpdir = copy_self()
    os.chdir(tmpdir)
    bbbb.build_sdist('test_sdist')
    assert 'test_sdist' in os.listdir()
    
