"""On-demand Hugging Face download for the Qwen Image 2.1 camera LoRA."""

import logging
from pathlib import Path

import folder_paths

REPO_ID = "akhaliq/Qwen-Image-2.1-Multiple-Angles-LoRA"
LORA_FILENAME = "angles_v2_full_qwen21_multiple_angles_v2_qwen21_multiple_angles_v2_000001500.safetensors"
HF_FILENAME = f"checkpoints_v2/{LORA_FILENAME}"


def ensure_lora() -> str:
    """Reuse configured LoRA paths (including subfolders), otherwise download."""
    for name in folder_paths.get_filename_list("loras"):
        if Path(name).name == LORA_FILENAME:
            path = folder_paths.get_full_path("loras", name)
            if path and Path(path).is_file() and Path(path).stat().st_size > 0:
                return path

    target = Path(folder_paths.models_dir) / "loras" / "qwen_image_2_1_multiple_angles"
    local_file = target / HF_FILENAME
    if local_file.is_file() and local_file.stat().st_size > 0:
        return str(local_file)

    try:
        from huggingface_hub import hf_hub_download
    except ImportError as exc:
        raise RuntimeError(
            "Install this node's requirements.txt in ComfyUI's Python environment "
            "to enable the automatic Hugging Face LoRA download."
        ) from exc

    logging.info("[QwenMultiangle] Downloading %s from %s", HF_FILENAME, REPO_ID)
    try:
        return hf_hub_download(repo_id=REPO_ID, filename=HF_FILENAME, local_dir=str(target))
    except Exception as exc:
        raise RuntimeError(
            f"Could not download {HF_FILENAME} from {REPO_ID}. Check your network "
            f"and Hugging Face access, or place {LORA_FILENAME} in a configured LoRA folder."
        ) from exc
