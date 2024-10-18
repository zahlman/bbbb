def _filter_implementation(path, exclude_tests):
    if path.name.startswith('.'):
        return False
    parts = path.parts
    if '__pycache__' in parts:
        return False
    if path.parts == ('sdist.py',): # self-exclusion
        return False
    # sdists and wheels created either normally or in tests.
    if parts[0] in ('dist', 'test_dist'):
        return False
    if 'tests' in parts and exclude_tests:
        return False
    return True


def example_filter(config, path):
    exclude_tests = False
    if 'exclude-tests' in config['commandline']:
        if config['commandline']['exclude-tests'] != '':
            raise ValueError("`exclude-tests` shouldn't have a value")
        exclude_tests = True
    bad_keys = set(config['commandline'].keys()) - {'exclude-tests'}
    if bad_keys:
        raise ValueError(f"unrecognized command-line options: {bad_keys}")
    return _filter_implementation(path, exclude_tests)
