def example_filter(config, path):
    if path.name.startswith('.'):
        return False
    parts = path.parts
    if '__pycache__' in parts:
        return False
    if path.parts == ('sdist.py',): # self-exclusion
        return False
    if parts[0] == 'dist':
        return False
    if 'test' in parts[0]: # not just the tests themselves,
        # but files/folders created by them.
        return False
    return True
