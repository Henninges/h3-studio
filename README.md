# h3-studio 🎬

A bilingual (EN/DE) web GUI for [antirez/h3.c](https://github.com/antirez/h3.c) focused on the **music-video workflow**: lip-synced video from reference image + audio in a single pass.

> **Note:** There's also [PR #45](https://github.com/antirez/h3.c/pull/45) "H3 Studio" – a native macOS desktop app with hardware-aware presets. This project (h3-studio) is a separate, web-based GUI specializing in audio+video conditioning and multilingual UI.

> **Unofficial community project.** Not affiliated with antirez or MiniMax.

## What is this?

[h3.c](https://github.com/antirez/h3.c) is Salvatore Sanfilippo's (antirez) native C/Metal inference engine for MiniMax H3 – the fastest way to run H3 on a Mac. But it is CLI-only. **h3-studio** wraps it in a widescreen browser dashboard:

- 📝 Simple mode (free prompt) **and** Advanced mode (Context-IR fields: Scene / Action / Camera / Look / Audio with smart defaults for empty fields)
- 🖼️ Up to **9 reference images**, 🎞️ 3 video refs, 🎵 3 audio refs (Ref2VA)
- 🥇 First/last-frame conditioning (FL2VA) with built-in conflict protection
- 🎚️ Resolution presets, frame/step/layer sliders, seed, reuse, token reduction
- 🌐 DE/EN toggle (remembered per browser)
- 📟 Live terminal log + automatic video preview

Perfect for music videos: reference image + song → **lip-synced video with native stereo audio in a single pass**. No more "silent render → LatentSync → merge" ping-pong.

## Requirements

- Apple Silicon Mac (tested on **M4 Max, 128 GB**)
- ~210 GB free SSD space
- Compiled `h3.c` (`make -j`) with official weights (see below)
- `ffmpeg` on PATH (`brew install ffmpeg`)
- Python 3 + Flask

## Quick start

**1.** Build h3.c, then download the weights *surgically* (~210 GB instead of ~340 GB):

```bash
hf download MiniMaxAI/MiniMax-H3 --local-dir ./MiniMax-H3 \
  --include "FL2VA/*" \
  --include "Ref2VA/transformer/*" \
  --include "Ref2VA/tokenizer/*" \
  --include "Ref2VA/model_index.json"
  
  2. Text encoder and both VAEs are byte-identical in both trees – save ~80 GB with symlinks:
  
  cd MiniMax-H3
ln -s ../FL2VA/text_encoder Ref2VA/text_encoder
ln -s ../FL2VA/audio_vae   Ref2VA/audio_vae
ln -s ../FL2VA/video_vae   Ref2VA/video_vae
cd ..

3. Put h3-studio next to the h3.c folder, then:

pip install -r requirements.txt
python3 app.py

4. Open http://127.0.0.1:5000 and direct your first take!

Optional: Turbo LoRA (6-step distilled sampling, ~1.5× faster)
Folds larryvrh/MiniMax-H3-Turbo-Lora (Apache-2.0) into a copy-on-write checkpoint variant (~2–3 GB real disk on APFS) using PR #14's tools/fold_turbo_lora.py. No engine changes needed – the folded checkpoint works with the stock h3 binary at --steps 6.

cd <h3.c folder>
mkdir -p tools
curl -L -o tools/fold_turbo_lora.py https://raw.githubusercontent.com/skaiy/h3.c-studio/main/tools/fold_turbo_lora.py
hf download larryvrh/MiniMax-H3-Turbo-Lora --local-dir ./turbo-lora

python3 tools/fold_turbo_lora.py --checkpoint ./MiniMax-H3/FL2VA/transformer  --lora ./turbo-lora/<adapter>.safetensors --out ./MiniMax-H3-Turbo/FL2VA/transformer
python3 tools/fold_turbo_lora.py --checkpoint ./MiniMax-H3/Ref2VA/transformer --lora ./turbo-lora/<adapter>.safetensors --out ./MiniMax-H3-Turbo/Ref2VA/transformer

cd MiniMax-H3-Turbo
ln -s ../../MiniMax-H3/FL2VA/model_index.json FL2VA/model_index.json
ln -s ../../MiniMax-H3/FL2VA/text_encoder FL2VA/text_encoder
ln -s ../../MiniMax-H3/FL2VA/audio_vae   FL2VA/audio_vae
ln -s ../../MiniMax-H3/FL2VA/video_vae   FL2VA/video_vae
ln -s ../../MiniMax-H3/Ref2VA/tokenizer  FL2VA/tokenizer
ln -s ../../MiniMax-H3/Ref2VA/tokenizer        Ref2VA/tokenizer
ln -s ../../MiniMax-H3/Ref2VA/model_index.json Ref2VA/model_index.json
ln -s ../../MiniMax-H3/Ref2VA/text_encoder Ref2VA/text_encoder
ln -s ../../MiniMax-H3/Ref2VA/audio_vae   Ref2VA/audio_vae
ln -s ../../MiniMax-H3/Ref2VA/video_vae   Ref2VA/video_vae
cd ..

⚠️ Rules (from PR #14): never combine the distilled schedule with --reuse/--core-reuse; floor is 5 steps. h3-studio enforces --steps 6 --reuse 1 automatically when Turbo is selected.
Benchmarks (real-world, end-to-end)
M4 Max, 128 GB (this repo's author)
Resolution	Frames	Steps / Layers	References	Time
512×512	243 (10 s)	20 / 45	1 image + audio	32 min (incl. cold weight load)
512×512	243 (10 s)	20 / 45	4 images + audio	21 min (warm cache)

Mode	Steps / reuse	Frames	Time (warm)	Notes
Standard	 20 / 2	56	4:23	full detail
Turbo	      6 / 1	56	3:00	~1.46× faster; fine detail (eyes, fingers) slightly softer

Recommendation: Turbo for prompt/composition iteration, Standard for final renders.

Benchmarks (real-world, end-to-end)
M4 Max, 128 GB (this repo's author)
Resolution      Frames      Steps/Layers    Reference       Time
512x512         243         20/45           1 Image+Audio   32min (incl.cold weight load)
512x512         243         20/45           4 Images+Audio  21min (warm cache) 

Community data (h3.c issues #5, #29, #30)
Machine             Resolution      Duration        Time
M4 Max 64 GB        960x544         10s             35min
M1 Max 64 GB        256x256         15s             6min
MacBook Air M5 32GB 512x512         1s              101sec

Prompt guide (hard-won lessons)

The model follows the described action, not keywords: write "sings the vocals" instead of "lip sync".
Clothing: state it explicitly (wearing a red dress) – or pin it with several consistent reference images.
References carry pose cues! A back-view picture may make the model turn the person around mid-video. Add "stays facing the camera, does not turn around" and "Pictures 2–4 are identity references only".
Audio: 2–15 s, pick a segment with continuous vocals for best sync.
Ref2VA (images/videos/audio) and FL2VA (first/last frame) cannot be mixed.

Community & Cross-pollination
Open source thrives when we build on each other's work. This project has learned from and inspired:
skaiy/h3.c-studio – Another web GUI for h3.c with storyboard/chaining features. Our Context-IR smart defaults and --ref-audio conditioning inspired features there; their Turbo LoRA integration and resumable checkpoints show what's possible. Different tools for different workflows: theirs for multi-shot storytelling, ours for music videos with native audio+video conditioning.
Roadmap
Turbo LoRA folding support (PR #14 tooling: 6-step distilled sampling, ~1.5× faster)
Song storyboard: cut tracks into ≤15s segments, render each with same references + segment audio, auto-concat
Chunked 5s workflow: first-frame chaining + FFmpeg concat button
Progress bar parsed from the live log
768p quality presets

Credits & License
h3.c © Salvatore Sanfilippo – MIT
MiniMax-H3 © MiniMax – own license; weights are not redistributed here
MiniMax-H3-Turbo-Lora © larryvrh – Apache-2.0
h3-studio – MIT
