# ComfyUI-qwenmultiangle — Qwen Image 2.1

Interactive 3D camera control for [akhaliq/Qwen-Image-2.1-Multiple-Angles-LoRA](https://huggingface.co/akhaliq/Qwen-Image-2.1-Multiple-Angles-LoRA).
This fork targets **Qwen Image 2.1** and uses the recommended **v2, step 1500** checkpoint. Older Edit models and their camera LoRAs are no longer supported.

## Installation

Install this fork in `ComfyUI/custom_nodes/ComfyUI-qwenmultiangle`, then run with ComfyUI's Python:

```sh
python -m pip install -r requirements.txt
```

Restart ComfyUI and refresh the browser. The compiled frontend is included.

## Usage

Open `workflow/image_qwen_image_2_1_multiangle_camera.json`. Select your reference image and installed Qwen Image 2.1 diffusion model, text encoder and VAE. This requires a ComfyUI version with `TextEncodeQwenImage21` support.

- Connect the Qwen Image 2.1 MODEL through **Qwen Image 2.1 Multiple Angles LoRA** to the sampler.
- Connect **Qwen Multiangle Camera**'s prompt directly to `TextEncodeQwenImage21` and the reference image to both nodes. The camera image input alone only provides a preview.
- Start with LoRA strength **1.0**; try **0.8** if needed. Strength 0 bypasses loading and downloading.
- Keep the camera prompt in English, without a prompt enhancer rewriting the trigger or pose labels.

The loader automatically downloads the missing LoRA on its first execution using `huggingface_hub.hf_hub_download` (the Hugging Face download API). It first searches all configured ComfyUI LoRA folders, including subfolders, for the exact checkpoint filename. Existing files work offline.

Repository file:

```
checkpoints_v2/angles_v2_full_qwen21_multiple_angles_v2_qwen21_multiple_angles_v2_000001500.safetensors
```

Default download directory: `ComfyUI/models/loras/qwen_image_2_1_multiple_angles/` (preserving the `checkpoints_v2` subfolder). The download is about 319 MB. Hugging Face handles partial downloads and file locking; failures show an actionable error and can be retried. Standard `HF_TOKEN` / saved HF credentials are supported if needed. Nothing downloads when merely importing the extension or using the prompt-only camera node.

For manual installation, put the exact checkpoint file in any configured LoRA folder, or use:

```sh
hf download akhaliq/Qwen-Image-2.1-Multiple-Angles-LoRA checkpoints_v2/angles_v2_full_qwen21_multiple_angles_v2_qwen21_multiple_angles_v2_000001500.safetensors --local-dir /path/to/ComfyUI/models/loras/qwen_image_2_1_multiple_angles
```

## Camera controls

Drag the 3D handles, use sliders or select presets. `camera_view` enables orbit preview; the image input displays your reference in the scene. Camera output IDs remain unchanged, but existing workflows must switch to the Qwen Image 2.1 model, encoding and LoRA loader.

The prompt uses the trained grammar:

```text
<mva> {azimuth}, {elevation}[ close-up]
```

Azimuths in 30-degree increments: front view, front-right view, front-right quarter view, right side view, back-right quarter view, back-right view, back view, back-left view, back-left quarter view, left side view, front-left quarter view, front-left view.

Elevations: 0° eye-level, 30° elevated, 60° high-angle, 90° top-down. Intermediate values map to the nearest trained pose; halfway values round upward, and 360° wraps to front view. Old negative elevations clamp to 0°.

Zoom 0–10 controls the preview distance. Below 6 the prompt uses standard framing (no suffix); at 6 or above it appends `close-up`. No wide/medium framing labels are emitted. `default_prompts` remains a compatibility input with no effect.

The optional **Qwen Multiangle Camera Translate** node translates camera terms to Chinese, Japanese or Korean and preserves `<mva>`. Translated prompts are experimental: this LoRA's documented grammar is English.

## Development

```sh
npm ci
npm run typecheck
npm run build
python -m unittest discover -s tests -v
```

Frontend: Vue 3, Three.js, TypeScript and Vite. Backend: ComfyUI V3 nodes. Built files in `js/` are committed for distribution. Tests exercise prompt mapping and local/download/error paths with ComfyUI and Hugging Face mocked; they do not perform GPU inference.

## Credits and license

Based on [jtydhr88/ComfyUI-qwenmultiangle](https://github.com/jtydhr88/ComfyUI-qwenmultiangle) and [amrrs/qwenmultiangle](https://github.com/amrrs/qwenmultiangle). LoRA by [akhaliq](https://huggingface.co/akhaliq/Qwen-Image-2.1-Multiple-Angles-LoRA), under its own Apache-2.0 license. Extension: MIT; see LICENSE.
