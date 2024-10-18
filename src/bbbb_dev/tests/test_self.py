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


TEST_DIR = Path(__file__).parent
BBBB_ROOT = TEST_DIR.parent.parent.parent


def _toplevel_not_src(src, names):
    # a filter for copytree.
    # Only copy the `src` folder when doing the self-test.
    src = Path(src)
    if src != BBBB_ROOT:
        return []
    return [n for n in names if (src / n).is_dir() and n != 'src']


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
    def _impl(project_path, config_rel_path, src_only):
        ignore = _toplevel_not_src if src_only else None
        copytree(project_path, tmpdir, ignore=ignore, dirs_exist_ok=True)
        os.chdir(tmpdir)
        # Determine project name and version for use in tests.
        with open('pyproject.toml', 'rb') as f:
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


def _verify_sdist(src_path, expected, name, version):
    _build('sdist', src_path, True)
    with open_tar(f'test_dist/{name}-{version}.tar.gz') as t:
        actual = sorted(m.path for m in t.getmembers())
    assert expected['sdist']['files'] == actual


def _verify_wheel(src_path, expected, name, version):
    _build('wheel', src_path, True)
    with ZipFile(f'test_dist/{name}-{version}-py3-none-any.whl') as z:
        actual = sorted(m.orig_filename for m in z.filelist)
    assert expected['wheel']['files'] == actual


def test_self_sdist(setup):
    _verify_sdist('.', *setup(BBBB_ROOT, '.', True))


def test_self_wheel(setup):
    _verify_wheel('.', *setup(BBBB_ROOT, '.', True))


def test_self_wheel_via_sdist(setup):
    # Include tests in the sdist to ensure the wheel filters them.
    expected, name, version = setup(BBBB_ROOT, '.', True)
    _build('sdist', '.', False)
    with open_tar(f'test_dist/{name}-{version}.tar.gz') as t:
        t.extractall(f'test_dist')
    # TODO: verify that there *are* tests extracted
    _verify_wheel(f'test_dist/{name}-{version}', expected, name, version)
