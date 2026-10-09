"""CPU-only contract tests; no model downloads or ComfyUI installation required."""

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class MultiangleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folders = types.ModuleType("folder_paths")
        cls.folders.get_filename_list = Mock(return_value=[])
        cls.folders.get_full_path = Mock(return_value=None)
        hub = types.ModuleType("huggingface_hub")
        hub.hf_hub_download = Mock()
        cls.hub = hub
        api = types.ModuleType("comfy_api.latest")
        api.ComfyExtension = type("ComfyExtension", (), {})
        api.io = types.SimpleNamespace(ComfyNode=type("ComfyNode", (), {}), NodeOutput=lambda *args, **kwargs: args)
        api.UI = object()
        private_io = types.ModuleType("comfy_api.latest._io")
        private_io._UIOutput = object
        private_io.FolderType = types.SimpleNamespace(temp="temp")
        private_ui = types.ModuleType("comfy_api.latest._ui")
        private_ui.ImageSaveHelper = Mock()
        private_ui.SavedResult = dict
        typing = types.ModuleType("typing_extensions")
        typing.override = lambda f: f
        pkg = types.ModuleType("multiangle_test_package")
        pkg.__path__ = [str(ROOT)]
        cls.modules = patch.dict(sys.modules, {
            "folder_paths": cls.folders, "huggingface_hub": hub,
            "comfy_api": types.ModuleType("comfy_api"), "comfy_api.latest": api,
            "comfy_api.latest._io": private_io, "comfy_api.latest._ui": private_ui,
            "typing_extensions": typing, "multiangle_test_package": pkg,
        })
        cls.modules.start()
        cls.addClassCleanup(cls.modules.stop)
        cls.lora = load("multiangle_test_package.lora", "lora.py")
        cls.nodes = load("multiangle_test_package.nodes", "nodes.py")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folders.models_dir = self.temp.name
        self.folders.get_filename_list.reset_mock(return_value=True)
        self.folders.get_filename_list.return_value = []
        self.folders.get_full_path.reset_mock(return_value=True)
        self.hub.hf_hub_download.reset_mock(return_value=True, side_effect=True)

    def test_pose_dictionary_and_framings(self):
        azimuths = ["front view", "front-right view", "front-right quarter view", "right side view", "back-right quarter view", "back-right view", "back view", "back-left view", "back-left quarter view", "left side view", "front-left quarter view", "front-left view"]
        elevations = ["eye-level shot", "elevated shot", "high-angle shot", "top-down shot"]
        for h, azimuth in enumerate(azimuths):
            for v, elevation in enumerate(elevations):
                for zoom, suffix in [(0, ""), (5.9, ""), (6, " close-up"), (10, " close-up")]:
                    output = self.nodes.QwenMultiangleCameraNode.execute(h * 30, v * 30, zoom)
                    self.assertEqual(output[0], f"<mva> {azimuth}, {elevation}{suffix}")

    def test_boundaries_and_old_elevation(self):
        camera = self.nodes.QwenMultiangleCameraNode
        self.assertEqual(camera.execute(360, -30, 5)[0], "<mva> front view, eye-level shot")
        self.assertEqual(camera.execute(15, 75, 6)[0], "<mva> front-right view, top-down shot close-up")
        self.assertEqual(camera.execute(345, 120, 5)[0], "<mva> front view, top-down shot")

    @unittest.skipUnless(shutil.which("node"), "Node.js not installed")
    def test_frontend_backend_prompt_parity(self):
        source = (ROOT / "src/CameraWidget.ts").read_text(encoding="utf-8")
        body = source.split("public generatePrompt(): string {", 1)[1].split("\n  public setState", 1)[0]
        # The method body is also plain JavaScript.
        script = "const camera = {state: {}, generatePrompt() {" + body + "};\n"
        cases = [(h, v, z) for h in [0, 14, 15, 29, 45, 90, 179, 300, 344, 345, 360] for v in [-30, 0, 14, 15, 44, 45, 74, 75, 90] for z in [0, 5.9, 6, 10]]
        script += "console.log(JSON.stringify(" + json.dumps(cases) + ".map(([azimuth,elevation,distance]) => {camera.state={azimuth,elevation,distance};return camera.generatePrompt()})))"
        actual = json.loads(subprocess.check_output([shutil.which("node"), "-e", script], text=True))
        self.assertEqual(actual, [self.nodes.QwenMultiangleCameraNode.execute(*case)[0] for case in cases])

    def test_existing_lora_in_extra_folder_avoids_download(self):
        local = Path(self.temp.name) / self.lora.LORA_FILENAME
        local.write_bytes(b"existing")
        self.folders.get_filename_list.return_value = ["nested/" + local.name]
        self.folders.get_full_path.return_value = str(local)
        self.assertEqual(self.lora.ensure_lora(), str(local))
        self.hub.hf_hub_download.assert_not_called()

    def test_download_and_reuse_without_refreshed_folder_cache(self):
        def download(**kwargs):
            path = Path(kwargs["local_dir"]) / kwargs["filename"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"downloaded")
            return str(path)
        self.hub.hf_hub_download.side_effect = download
        first = self.lora.ensure_lora()
        self.assertEqual(self.lora.ensure_lora(), first)
        self.hub.hf_hub_download.assert_called_once_with(
            repo_id=self.lora.REPO_ID, filename=self.lora.HF_FILENAME,
            local_dir=str(Path(self.temp.name) / "loras" / "qwen_image_2_1_multiple_angles"),
        )

    def test_failed_download_can_retry(self):
        self.hub.hf_hub_download.side_effect = OSError("offline")
        with self.assertRaisesRegex(RuntimeError, "Check your network"):
            self.lora.ensure_lora()
        self.hub.hf_hub_download.side_effect = None
        self.hub.hf_hub_download.return_value = "downloaded.safetensors"
        self.assertEqual(self.lora.ensure_lora(), "downloaded.safetensors")

    def test_loader_applies_model_only_and_zero_bypasses(self):
        model = object()
        with patch.object(self.nodes, "ensure_lora", return_value="local.safetensors") as ensure:
            self.assertEqual(self.nodes.QwenMultiangleLoraLoader.execute(model, 0), (model,))
            ensure.assert_not_called()
            comfy = types.ModuleType("comfy")
            comfy.sd = types.ModuleType("comfy.sd")
            comfy.utils = types.ModuleType("comfy.utils")
            comfy.utils.load_torch_file = Mock(return_value={"weights": 1})
            comfy.sd.load_lora_for_models = Mock(return_value=("patched", None))
            with patch.dict(sys.modules, {"comfy": comfy, "comfy.sd": comfy.sd, "comfy.utils": comfy.utils}):
                self.assertEqual(self.nodes.QwenMultiangleLoraLoader.execute(model, 0.8), ("patched",))
            comfy.utils.load_torch_file.assert_called_once_with("local.safetensors", safe_load=True)
            comfy.sd.load_lora_for_models.assert_called_once_with(model, None, {"weights": 1}, 0.8, 0)


if __name__ == "__main__":
    unittest.main()
