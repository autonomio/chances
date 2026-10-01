"""The bootstrap file rewrite renames the package but preserves the template slug.

References to the template's own slug (`Autonomio/new-repository-template`) -- the
README provenance link, the SETUP runbook's `--template` command, the label
source -- must survive specialization unchanged, even though every other
occurrence of the seed package name is rewritten.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]




def _tree_hashes(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in sorted(root.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts:
            out[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def test_template_slug_survives_file_bootstrap(seed_repository: Path) -> None:
    repo = seed_repository
    result = subprocess.run(
        [
            sys.executable, 'governance/bootstrap_repository.py', '--files-only',
            '--repo-name', 'my-new-app', '--owner', 'Autonomio',
        ],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr + result.stdout

    # The rewrite actually ran: the seed package is renamed and gone.
    assert (repo / 'my_new_app').is_dir()
    assert not (repo / 'new_repository_template').exists()
    assert 'new_repository_template' not in (repo / 'pyproject.toml').read_text(encoding='utf-8')

    # ...but references to the template's own slug are preserved verbatim.
    readme = (repo / 'README.md').read_text(encoding='utf-8')
    assert 'https://github.com/Autonomio/new-repository-template' in readme
    setup = (repo / 'SETUP.md').read_text(encoding='utf-8')
    assert '--template Autonomio/new-repository-template' in setup
    docs_profile = json.loads(
        (repo / 'docs-site' / 'product-docs.json').read_text(encoding='utf-8')
    )
    assert docs_profile == {
        'productId': 'my-new-app',
        'productName': 'My New App',
        'tagline': 'Python package with repository law built in.',
        'siteUrl': 'https://autonomio.github.io',
        'basePath': '/my-new-app/',
        'sourceRepoUrl': 'https://github.com/Autonomio/my-new-app',
        'sourceBranch': 'master',
    }


def test_file_bootstrap_is_idempotent(seed_repository: Path) -> None:
    # A deliberate files-only rerun must preserve specialized identity and
    # tuned budgets; live activation is a separate reviewed process.
    repo = seed_repository
    cmd = [
        sys.executable, 'governance/bootstrap_repository.py', '--files-only',
        '--repo-name', 'my-new-app', '--owner', 'Autonomio',
    ]
    first = subprocess.run(cmd, cwd=repo, check=False, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr + first.stdout
    assert (repo / 'my_new_app').is_dir()

    # Tune a module budget the way a real slice does -- the exact value the
    # unguarded rewrite would otherwise replace.
    budget_path = repo / '.github' / 'budgets.json'
    budgets = json.loads(budget_path.read_text(encoding='utf-8'))
    budgets['modules']['my_new_app/__init__.py'] = 999
    budget_path.write_text(json.dumps(budgets, indent=2) + '\n', encoding='utf-8')

    before = _tree_hashes(repo)
    second = subprocess.run(cmd, cwd=repo, check=False, capture_output=True, text=True)
    assert second.returncode == 0, second.stderr + second.stdout
    assert 'already specialized' in second.stdout
    assert _tree_hashes(repo) == before, 'second bootstrap run must change nothing'
    # The tuned budget survived: the re-run did not regenerate it.
    reread = json.loads(budget_path.read_text(encoding='utf-8'))
    assert reread['modules']['my_new_app/__init__.py'] == 999
