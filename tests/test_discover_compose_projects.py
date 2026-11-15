"""Offline safety checks for Docker Compose discovery."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "scripts/discover_compose_projects.py"
spec = importlib.util.spec_from_file_location("fleet_discovery", SOURCE)
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)


def fake(name, project=None, service=None, root=None, config=None, image="demo/app:latest", mounts=None, env=None):
    labels = {}
    if project:
        labels = {
            "com.docker.compose.project": project,
            "com.docker.compose.service": service,
            "com.docker.compose.project.working_dir": str(root),
            "com.docker.compose.project.config_files": str(config),
        }
        if env:
            labels["com.docker.compose.project.environment_file"] = env
    return {"Name": "/" + name, "Config": {"Labels": labels, "Image": image}, "Mounts": mounts or []}


class Tests(unittest.TestCase):
    def test_valid_project(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            file = root / "compose.yml"
            file.write_text("services:\n  app:\n    image: demo/app:latest\n")
            c = fake("app", "demo", "app", root, file)
            with patch.object(d, "run", return_value=json.dumps({"services": {"app": {"image": "demo/app:latest"}}})):
                result = d.inspect_inventory([c], [])
            self.assertTrue(result["projects"]["demo"]["eligible"])

    def test_bad_mount_is_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            file = root / "compose.yml"
            file.touch()
            c = fake("app", "demo", "app", root, file, mounts=[
                {"Type": "bind", "Source": "/old", "Destination": "/config"}
            ])
            model = {"services": {"app": {"image": "demo/app:latest", "volumes": [
                {"type": "bind", "source": "/new", "target": "/config"}
            ]}}}
            with patch.object(d, "run", return_value=json.dumps(model)):
                result = d.inspect_inventory([c], [])
            self.assertFalse(result["projects"]["demo"]["eligible"])

    def test_explicit_env_file_is_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            file = root / "compose.yml"
            file.touch()
            c = fake("app", "demo", "app", root, file, env="/tmp/stack.env")
            self.assertFalse(d.inspect_inventory([c], [])["projects"]["demo"]["eligible"])

    def test_portainer_path_remap_is_review_only(self):
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp) / "data"
            file = data / "compose" / "42" / "compose.yml"
            file.parent.mkdir(parents=True)
            file.touch()
            manager = {
                "Name": "/portainer",
                "Config": {"Image": "portainer/portainer-ce:latest", "Labels": {}},
                "Mounts": [{"Type": "bind", "Source": str(data), "Destination": "/data"}]
            }
            c = fake("app", "demo", "app", "/data/compose/42", "/data/compose/42/compose.yml")
            result = d.inspect_inventory([c], d.manager_mounts([manager]))["projects"]["demo"]
            self.assertFalse(result["eligible"])
            self.assertEqual(result["working_dir"], str(file.parent))

    def test_config_merge_preserves_token_and_permissions(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config.json"
            path.write_text(json.dumps({"token": "hidden", "allowed_actions": [], "compose_projects": {}}))
            path.chmod(0o600)
            inventory = {"projects": {"demo": {"eligible": True, "working_dir": "/x",
                                                 "files": ["/x/compose.yml"]}}}
            added, existing = d.apply_config(path, inventory, False)
            self.assertEqual(added, ["demo"])
            self.assertEqual(existing, [])
            self.assertEqual(json.loads(path.read_text())["token"], "hidden")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(len(list(Path(temp).glob("config.json.bak-*"))), 1)

    def test_action_permission_scope_is_confirmed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config.json"
            path.write_text(json.dumps({"allowed_actions": ["compose_update"], "compose_projects": {}}))
            with self.assertRaises(d.DiscoveryError):
                d.apply_config(path, {"projects": {}}, False)


if __name__ == "__main__":
    unittest.main()
