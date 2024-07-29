def example_filter(config, path):
    if path.name.startswith('.'):
        return False
    if path.parts == ('dist',):
        return False
    if '__pycache__' in path.parts:
        return False
    if path.parts == ('sdist.py',): # self-exclusion
        return False
    return True
