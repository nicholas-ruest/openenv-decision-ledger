import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('public_dataset_audit', Path(__file__).parents[3] / 'scripts/audit-public-software-dataset.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_task_identity_does_not_coerce_booleans_integers_or_container_types():
    assert audit.digest(True) != audit.digest(1)
    assert audit.digest([1, 2]) != audit.digest((1, 2))
    assert audit.digest({'a': 1, 'b': 2}) != audit.digest({'b': 2, 'a': 1})
    with pytest.raises(ValueError, match='nonfinite'):
        audit.digest(float('nan'))


@pytest.mark.parametrize('actual,dirty', [('wrong', ''), (audit.CURRENT, ' M changed.py')])
def test_dirty_or_wrong_revision_cannot_supply_task_correspondence(monkeypatch, tmp_path, actual, dirty):
    monkeypatch.setattr(audit.subprocess, 'check_output', lambda args, **kw: actual if 'rev-parse' in args else dirty)
    with pytest.raises(ValueError, match='clean pinned source'):
        audit.checked_root(tmp_path, audit.CURRENT)
