import os
import subprocess
from flask import Flask, render_template, request, Response, send_from_directory

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def find_h3_home():
    """Findet den Ordner mit h3-Binary + MiniMax-H3-Gewichten."""
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

# ---- Der "Text-Interpreter": Context-IR-Defaults für leere Felder ----
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

    # ---- Prompt: Simple oder Advanced (Context-IR) ----
    if request.form.get('mode') == 'advanced':
        prompt = build_context_ir(request.form)
    else:
        prompt = (request.form.get('prompt') or "").strip()
        if not prompt:
            prompt = build_context_ir(request.form)

    canvas = request.form.get('canvas', '512x512')
    width, height = canvas.split('x')

    out_path = os.path.join(OUTPUT_FOLDER, "result.mp4")
    cmd = [
        os.path.join(H3_HOME, "h3"), "-d", os.path.join(H3_HOME, "MiniMax-H3"),
        "-p", prompt,
        "--width", width, "--height", height,
        "--frames", request.form.get('frames', '107'),
        "--steps",  request.form.get('steps', '20'),
        "--layers", request.form.get('layers', '45'),
        "--reuse",  request.form.get('reuse', '2'),
        "--seed",   request.form.get('seed', '42'),
        "--profile", "-o", out_path,
    ]
    if request.form.get('token_reduction'):
        cmd.append("--token-reduction")

    # ---- Referenzen einsammeln (leere Slots werden ignoriert) ----
    imgs = [p for p in (save_upload(f'ref_image_{i}', f'img{i}') for i in range(1, 10)) if p]
    auds = [p for p in (save_upload(f'ref_audio_{i}', f'aud{i}') for i in range(1, 4)) if p]
    vids = []
    for i in range(1, 4):
        p = save_upload(f'ref_video_{i}', f'vid{i}')
        if p:
            vids.append((p, request.form.get(f'video_mode_{i}', 'silent')))
    first = save_upload('first_frame', 'first')
    last  = save_upload('last_frame', 'last')

    # ---- Schutzschaltungen ----
    if (imgs or auds or vids) and (first or last):
        return error_stream("References (Ref2VA) and first/last frame (FL2VA) cannot be combined!")
    if auds and not imgs and not vids:
        return error_stream("Audio references need at least one image or video!")

    # Reihenfolge wichtig: Bilder -> Videos -> Audios
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
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True)
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