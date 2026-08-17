h3-studio 🎬

A bilingual (EN/DE) web GUI for [antirez/h3.c](https://github.com/antirez/h3.c) – native MiniMax-H3 audio+video inference on Apple Silicon.

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

Roadmap
Chunked 5 s workflow: first-frame chaining + FFmpeg concat button
Progress bar parsed from the live log
Turbo-LoRA fast preset (once h3.c PR #14 lands)
768p quality presets

Credits & License
h3.c © Salvatore Sanfilippo – MIT
MiniMax-H3 © MiniMax – own license; weights are not redistributed here
h3-studio – MIT
