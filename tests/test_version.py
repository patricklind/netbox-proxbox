import ast
import tomllib
from pathlib import Path


ROOT = Path(__file__).parents[1]


def _plugin_version():
    tree = ast.parse((ROOT / 'proxmox2netbox' / '__init__.py').read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == 'Proxmox2NetBoxConfig':
            for statement in node.body:
                if (
                    isinstance(statement, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == 'version' for target in statement.targets)
                ):
                    return ast.literal_eval(statement.value)
    raise AssertionError('Proxmox2NetBoxConfig.version was not found')


def test_project_and_plugin_versions_match():
    with (ROOT / 'pyproject.toml').open('rb') as pyproject:
        project_version = tomllib.load(pyproject)['project']['version']

    assert project_version == _plugin_version()
