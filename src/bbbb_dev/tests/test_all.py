# Standard library
from os import chdir
from pathlib import Path
from shutil import copytree
from tarfile import open as open_tar
from zipfile import ZipFile

# third-party
import build
from pytest import fixture, mark, param
parametrize = mark.parametrize


try:
    from tomllib import load as load_toml # requires 3.11+
except ImportError: # 3.10 or earlier, so not in the standard library
    from tomli import load as load_toml # third-party implementation.


TEST_DIR = Path(__file__).parent


def _read_config(filename):
    with open(filename, 'rb') as f:
        result = load_toml(f) # let errors propagate
    # The `result` is newly created, so we may sort in-place.
    result['sdist']['files'].sort()
    result['wheel']['files'].sort()
    result['wheel']['record_lines'].sort()
    return result


@fixture
def setup(tmpdir):
    def _impl(project_folder, project_name):
        src_path = TEST_DIR / project_folder / project_name
        toml_path = TEST_DIR / project_folder / f'{project_name}.toml'
        copytree(src_path, tmpdir / 'project', dirs_exist_ok=True)
        chdir(tmpdir)
        # Determine expectations for resulting sdist and wheel.
        return _read_config(toml_path)
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


def _verify_sdist(src_path, expected):
    _build('sdist', src_path, True)
    with _find_sdist() as t:
        actual = sorted(m.path for m in t.getmembers())
    assert expected['sdist']['files'] == actual


def _verify_wheel(src_path, expected):
    _build('wheel', src_path, True)
    with _find_wheel() as z:
        actual = sorted(m.orig_filename for m in z.filelist)
    assert expected['wheel']['files'] == actual


def _verify_wheel_via_sdist(src_path, expected):
    # Include tests in the sdist to ensure the wheel filters them.
    _build('sdist', src_path, False)
    with _find_sdist() as t:
        t.extractall(f'test_dist')
    # TODO: verify that there *are* tests extracted
    _verify_wheel(_find_sdist_folder(), expected)


_verifiers = (
    param(_verify_sdist, id='sdist'),
    param(_verify_wheel, id='wheel'),
    param(_verify_wheel_via_sdist, id='wheel via sdist')
)
@parametrize('verifier', _verifiers)
def test_good(setup, verifier):
    verifier('project', setup('good-projects', 'minimal-src-layout'))
