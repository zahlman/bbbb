# Standard library
from os import chdir
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


TEST_DIR = Path(__file__).parent
BBBB_ROOT = TEST_DIR.parent.parent.parent


def _read_config(filename, project_name, project_version):
    with open(filename, 'rb') as f:
        result = load_toml(f) # let errors propagate
    result['sdist']['files'] = sorted(result['sdist']['files'])
    result['wheel']['files'] = sorted(result['wheel']['files'])
    result['wheel']['sha256'] = sorted(result['wheel']['sha256'])
    result['wheel']['size'] = sorted(result['wheel']['size'])
    return result


@pytest.fixture
def setup(tmpdir):
    def _impl(project_path, config_rel_path):
        copytree(project_path, tmpdir / 'project', dirs_exist_ok=True)
        chdir(tmpdir)
        # Determine project name and version for use in tests.
        with open('project/pyproject.toml', 'rb') as f:
            project = load_toml(f)['project']
        name, version = project['name'], project['version']
        # Determine expectations for resulting sdist and wheel.
        toml_path = TEST_DIR / config_rel_path / f'{name}.toml'
        return _read_config(toml_path, name, version), name, version
    return _impl


def _build(kind, src, exclude_tests):
    # Conform to the interface implied by expected command-line behaviour.
    config_settings = {'exclude-tests': ''} if exclude_tests else {}
    build.ProjectBuilder(src).build(kind, 'test_dist', config_settings)


def _find_sdist():
    paths = list(Path('test_dist').glob('*.tar.gz'))
    assert len(paths) == 1
    path = str(paths[0])
    assert path.count('-') == 1 # between name and version
    return open_tar(path)


def _find_wheel():
    paths = list(Path('test_dist').glob('*.whl'))
    assert len(paths) == 1
    path = str(paths[0])
    assert path.count('-') == 4 # after name, after version, 2 in wheel tags
    return ZipFile(path)


def _find_sdist_folder():
    dirs = [x for x in Path('test_dist').iterdir() if x.is_dir()]
    assert len(dirs) == 1
    dirname = str(dirs[0])
    assert dirname.count('-') == 1 # between name and version
    return dirname


def _verify_sdist(src_path, expected, name, version):
    _build('sdist', src_path, True)
    with _find_sdist() as t:
        actual = sorted(m.path for m in t.getmembers())
    assert expected['sdist']['files'] == actual


def _verify_wheel(src_path, expected, name, version):
    _build('wheel', src_path, True)
    with _find_wheel() as z:
        actual = sorted(m.orig_filename for m in z.filelist)
    assert expected['wheel']['files'] == actual


def _verify_wheel_via_sdist(src_path, expected, name, version):
    # Include tests in the sdist to ensure the wheel filters them.
    _build('sdist', src_path, False)
    with _find_sdist() as t:
        t.extractall(f'test_dist')
    # TODO: verify that there *are* tests extracted
    _verify_wheel(_find_sdist_folder(), expected, name, version)


def test_good_sdist(setup):
    _verify_sdist('project', *setup(TEST_DIR / 'good-projects' / 'minimal-src-layout', 'good-projects'))


def test_good_wheel(setup):
    _verify_wheel('project', *setup(TEST_DIR / 'good-projects' / 'minimal-src-layout', 'good-projects'))


def test_good_wheel_via_sdist(setup):
    _verify_wheel_via_sdist('project', *setup(TEST_DIR / 'good-projects' / 'minimal-src-layout', 'good-projects'))
