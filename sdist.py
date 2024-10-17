def example_filter(config, path):
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
    # Exclude src/tests for now. TODO make this optional
    if parts[:2] == ('src', 'tests'):
        return False
    return True
