"""The profiler identifies function bodies behind scoped entry points."""
import importlib.util
from pathlib import Path

from borethm import model1_coupled as m1


def test_scoped_functions_have_separate_observer_codes():
    path = Path(__file__).resolve().parents[1] / 'tools/profile_evaluation.py'
    spec = importlib.util.spec_from_file_location('profile_observer_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    observer = module.Observer.__new__(module.Observer)
    observer.codes = {}
    @m1._cache_solves
    def evaluate():
        return 1
    @m1._cache_solves
    def trial():
        return 2
    assert evaluate.__code__ is trial.__code__
    observer.register('evaluation', evaluate)
    observer.register('study', trial)
    assert len(observer.codes) == 2
    assert observer.codes[evaluate.__wrapped__.__code__]['stage'] == 'evaluation'
    assert observer.codes[trial.__wrapped__.__code__]['stage'] == 'study'
