import os
import subprocess
from flask import Flask, render_template, request, Response, send_from_directory

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def find_h3_home():
    candidates = [
        os.environ.get("H3_HOME", ""),
        BASE_DIR,
        os.path.join(os.path.dirname(BASE_DIR), "h3.c"),
    ]
    for c in candidates:
        if c and os.path.isfile(os.path.join(c, "h3")) \
               and os.path.isdir(os.path.join(c, "MiniMax-H3")):
            return c
    return None

H3_HOME = find_h3_home()

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "outputs")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

DEFAULTS = {
    "scene":  "the person shown in the reference pictures, in a natural, detailed setting",
    "action": "the person sings the vocals of the song, lips move in perfect sync with the voice, natural blinking, subtle facial expression",
    "camera": "medium shot, stable framing, gentle slow movement, subject stays in focus",
    "look":   "photorealistic, natural lighting, fine skin and hair detail",
    "audio":  "clear lead vocals singing the lyrics exactly as in the reference audio",
}

def build_context_ir(form):
    parts = []
    for key, label in [("scene", "Scene"), ("action", "Action"),
                       ("camera", "Camera"), ("look", "Look"), ("audio", "Audio")]:
        val = (form.get(key) or "").strip()
        parts.append(f"{label}: {val if val else DEFAULTS[key]}")
    return "\n".join(parts)

def save_upload(field, prefix):
    if field in request.files and request.files[field].filename != '':
        f = request.files[field]
        path = os.path.join(UPLOAD_FOLDER, prefix + os.path.splitext(f.filename)[1])
        f.save(path)
        return path
    return None

def error_stream(msg):
    def gen():
        yield f"data: ERROR: {msg}\n\n"
    return Response(gen(), mimetype='text/event-stream')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    if H3_HOME is None:
        return error_stream("h3 binary / MiniMax-H3 not found. Put h3-studio next to h3.c or set H3_HOME.")

    if request.form.get('mode') == 'advanced':
        prompt = build_context_ir(request.form)
    else:
        prompt = (request.form.get('prompt') or "").strip()
        if not prompt:
            prompt = build_context_ir(request.form)

    # ---- Modell wählen: Standard oder gefoldetes Turbo ----
    turbo = request.form.get('model') == 'turbo'
    model_dir = os.path.join(H3_HOME, "MiniMax-H3-Turbo" if turbo else "MiniMax-H3")
    if turbo and not os.path.isdir(model_dir):
        return error_stream("Turbo model not found. Fold it first (see README: tools/fold_turbo_lora.py).")

    # ---- Quality-Preset (kein --token-reduction: verursacht Geisterbilder!) ----
    quality = request.form.get('quality', 'balanced')
    if quality == 'fast':
        width, height = '512', '512'
        reuse = '3'
    elif quality == 'high':
        width, height = '768', '768'
        reuse = '2'
    else:
        width, height = '512', '512'
        reuse = '2'

    # ---- Turbo erzwingt destillierte Schedule: 6 Steps, reuse 1 (PR #14 Warnung!) ----
    if turbo:
        steps, reuse = '6', '1'
    else:
        steps = request.form.get('steps', '20')

    out_path = os.path.join(OUTPUT_FOLDER, "result.mp4")
    cmd = [
        os.path.join(H3_HOME, "h3"), "-d", model_dir,
        "-p", prompt,
        "--width", width, "--height", height,
        "--frames", request.form.get('frames', '107'),
        "--steps",  steps,
        "--layers", request.form.get('layers', '45'),
        "--reuse",  reuse,
        "--seed",   request.form.get('seed', '42'),
        "--profile", "-o", out_path,
    ]

    imgs = [p for p in (save_upload(f'ref_image_{i}', f'img{i}') for i in range(1, 10)) if p]
    auds = [p for p in (save_upload(f'ref_audio_{i}', f'aud{i}') for i in range(1, 4)) if p]
    vids = []
    for i in range(1, 4):
        p = save_upload(f'ref_video_{i}', f'vid{i}')
        if p:
            vids.append((p, request.form.get(f'video_mode_{i}', 'silent')))
    first = save_upload('first_frame', 'first')
    last  = save_upload('last_frame', 'last')

    if (imgs or auds or vids) and (first or last):
        return error_stream("References (Ref2VA) and first/last frame (FL2VA) cannot be combined!")
    if auds and not imgs and not vids:
        return error_stream("Audio references need at least one image or video!")

    for p in imgs:
        cmd.extend(["--ref-image", p])
    for p, mode in vids:
        cmd.extend(["--ref-video" if mode == 'keep' else "--ref-silent-video", p])
    for p in auds:
        cmd.extend(["--ref-audio", p])
    if first:
        cmd.extend(["--first-frame", first])
    if last:
        cmd.extend(["--last-frame", last])

    def stream():
        for pline in prompt.split("\n"):
            yield f"data: [Prompt] {pline}\n\n"
        if turbo:
            yield "data: [Model] Turbo LoRA folded checkpoint - 6 steps, reuse 1\n\n"
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, cwd=H3_HOME)
        for line in iter(process.stdout.readline, ''):
            yield f"data: {line.strip()}\n\n"
        process.stdout.close()
        yield "data: DONE\n\n"

    return Response(stream(), mimetype='text/event-stream')

@app.route('/video')
def video():
    return send_from_directory(OUTPUT_FOLDER, 'result.mp4')

if __name__ == '__main__':
    print("h3-studio läuft! Öffne im Browser: http://127.0.0.1:5000")
    app.run(port=5000, debug=False, threaded=True)
