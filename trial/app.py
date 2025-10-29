import os
import sqlite3
from pathlib import Path
from typing import Optional, Tuple, List, Dict

from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, session, jsonify
from werkzeug.utils import secure_filename

from PIL import Image, ImageFilter, ImageOps
import pytesseract

# Import new features
from features.interaction_checker import check_medicine_interactions
from features.pill_identifier import identify_pill_from_image
from features.severity_analyzer import analyze_side_effect_severity
from features.user_auth import UserAuthManager
from features.chatbot import get_chatbot_response
from features.translator import translate_text, Translator, SUPPORTED_LANGUAGES
from features.n8n_webhooks import api_bp

try:
    from rapidfuzz import fuzz, process as rapid_process
    RAPIDFUZZ_AVAILABLE = True
except Exception:
    RAPIDFUZZ_AVAILABLE = False


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "medicine.db"
CSV_PATH = BASE_DIR / "Medicine.csv"
UPLOAD_DIR = BASE_DIR / "uploads"

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

# Initialize feature managers
auth_manager = UserAuthManager(str(DB_PATH))


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "change-me")
    app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)

    _ensure_dirs()
    _configure_tesseract_on_windows()
    
    # n8n integration removed per request; running fully local Flask
    
    # Get selected language from session or default to English
    def get_language():
        return session.get("language", "en")

    # Make language data available to all templates
    @app.context_processor
    def inject_global_template_vars():
        return {
            "supported_languages": SUPPORTED_LANGUAGES,
            "current_lang": get_language(),
        }
    
    @app.route("/")
    def index():
        lang = get_language()
        return render_template("index.html", current_lang=lang, supported_languages=SUPPORTED_LANGUAGES)

    @app.route("/upload", methods=["POST"])
    def upload():
        if "image" not in request.files:
            flash("No file part in the request")
            return redirect(url_for("index"))

        file = request.files["image"]
        if file.filename == "":
            flash("No file selected")
            return redirect(url_for("index"))

        if not _allowed_file(file.filename):
            flash("Unsupported file type. Please upload png, jpg, jpeg, or webp.")
            return redirect(url_for("index"))

        filename = secure_filename(file.filename)
        saved_path = UPLOAD_DIR / filename
        file.save(saved_path)

        try:
            extracted_text = _extract_text_from_image(saved_path)
            heading_text = _extract_heading_from_image(saved_path)
        except Exception as e:
            flash(f"OCR failed: {e}")
            return redirect(url_for("index"))

        if not extracted_text.strip():
            return render_template(
                "result.html",
                query_text="",
                match=None,
                candidates=[],
                image_path=f"uploads/{filename}",
                heading_text=heading_text,
                heading_match_score=None,
                heading_matches=False,
            )

        match, candidates = _find_best_match(extracted_text)

        heading_match_score: Optional[float] = None
        heading_matches: bool = False
        if match and (heading_text or "").strip():
            heading_match_score = _compute_match_score(heading_text, match["medicine_name"])  # 0..100
            heading_matches = heading_match_score >= 75.0

        # Analyze side effects severity
        side_effects_analysis = None
        if match and match.get("side_effects"):
            side_effects_analysis = analyze_side_effect_severity(match["side_effects"])
        
        # Check user allergies if logged in
        allergy_warnings = []
        if "user_id" in session:
            allergy_check = auth_manager.check_allergy_conflict(session["user_id"], match.get("composition", "") if match else "")
            allergy_warnings = allergy_check.get("warnings", [])
        
        # Get language for translation
        lang = get_language()
        translator = Translator()
        
        # Translate medicine data if needed
        translated_match = match
        if match and lang != "en":
            translated_match = translator.translate_medicine_data(match, lang)
        
        return render_template(
            "result.html",
            query_text=extracted_text,
            match=translated_match or match,
            candidates=candidates,
            image_path=f"uploads/{filename}",
            heading_text=heading_text,
            heading_match_score=heading_match_score,
            heading_matches=heading_matches,
            side_effects_analysis=side_effects_analysis,
            allergy_warnings=allergy_warnings,
            current_lang=lang,
        )

    @app.route("/uploads/<path:filename>")
    def uploaded_file(filename: str):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    @app.route("/search", methods=["GET"]) 
    def search():
        query = request.args.get("q", "").strip()
        if not query:
            flash("Please enter a medicine name to search.")
            return redirect(url_for("index"))
        match, candidates = _find_best_match(query)
        # For text search, we don't have an image heading; still compute confidence against query's first line as a proxy
        first_line = (query.splitlines()[0] if query else "").strip()
        heading_match_score: Optional[float] = None
        heading_matches: bool = False
        if match and first_line:
            heading_match_score = _compute_match_score(first_line, match["medicine_name"])  # 0..100
            heading_matches = heading_match_score >= 75.0
        # Analyze side effects severity
        side_effects_analysis = None
        if match and match.get("side_effects"):
            side_effects_analysis = analyze_side_effect_severity(match["side_effects"])
        
        # Check user allergies if logged in
        allergy_warnings = []
        if "user_id" in session:
            allergy_check = auth_manager.check_allergy_conflict(session["user_id"], match.get("composition", "") if match else "")
            allergy_warnings = allergy_check.get("warnings", [])
        
        # Translate if needed
        lang = get_language()
        translator = Translator()
        translated_match = match
        if match and lang != "en":
            translated_match = translator.translate_medicine_data(match, lang)
        
        return render_template(
            "result.html",
            query_text=query,
            match=translated_match or match,
            candidates=candidates,
            image_path=None,
            heading_text=first_line or None,
            heading_match_score=heading_match_score,
            heading_matches=heading_matches,
            side_effects_analysis=side_effects_analysis,
            allergy_warnings=allergy_warnings,
            current_lang=lang,
        )
    
    # ==================== NEW FEATURE ROUTES ====================
    
    # User Authentication Routes
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            
            user = auth_manager.authenticate_user(username, password)
            if user:
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                flash("Login successful!")
                return redirect(url_for("index"))
            else:
                flash("Invalid username or password")
        
        return render_template("login.html", current_lang=get_language())
    
    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "")
            password_confirm = request.form.get("password_confirm", "")
            
            if password != password_confirm:
                flash("Passwords do not match")
                return redirect(url_for("register"))
            
            result = auth_manager.register_user(username, email, password)
            if result["status"] == "success":
                flash("Registration successful! Please login.")
                return redirect(url_for("login"))
            else:
                flash(result["message"])
        
        return render_template("register.html", current_lang=get_language())
    
    @app.route("/logout")
    def logout():
        session.clear()
        flash("Logged out successfully")
        return redirect(url_for("index"))
    
    @app.route("/profile", methods=["GET", "POST"])
    def profile():
        if "user_id" not in session:
            flash("Please login to access your profile")
            return redirect(url_for("login"))
        
        user_id = session["user_id"]
        
        if request.method == "POST":
            # Update profile
            profile_data = {
                "age": request.form.get("age"),
                "weight_kg": request.form.get("weight_kg"),
                "height_cm": request.form.get("height_cm"),
                "gender": request.form.get("gender"),
            }
            
            # Clean empty strings
            profile_data = {k: v if v else None for k, v in profile_data.items()}
            
            auth_manager.update_medical_profile(user_id, **profile_data)
            flash("Profile updated!")
            return redirect(url_for("profile"))
        
        # Get current profile
        profile = auth_manager.get_medical_profile(user_id)
        allergies = auth_manager.get_allergies(user_id)
        
        return render_template("profile.html", profile=profile, allergies=allergies, current_lang=get_language())
    
    @app.route("/allergies", methods=["POST"])
    def add_allergy():
        if "user_id" not in session:
            return jsonify({"error": "Not logged in"}), 401
        
        allergen_name = request.form.get("allergen_name", "").strip()
        if not allergen_name:
            flash("Please enter an allergen name")
            return redirect(url_for("profile"))
        
        result = auth_manager.add_allergy(
            session["user_id"],
            allergen_name,
            request.form.get("allergen_type"),
            request.form.get("severity", "moderate"),
            request.form.get("notes")
        )
        
        flash(result.get("message", "Allergy added"))
        return redirect(url_for("profile"))
    
    # Medicine Interaction Checker
    @app.route("/interactions", methods=["GET", "POST"])
    def check_interactions():
        if request.method == "POST":
            medicines_str = request.form.get("medicines", "")
            medicines = [m.strip() for m in medicines_str.split(",") if m.strip()]
            
            if len(medicines) < 2:
                flash("Please enter at least 2 medicines")
                return redirect(url_for("check_interactions"))
            
            result = check_medicine_interactions(medicines)
            return render_template("interactions.html", result=result, current_lang=get_language())
        
        return render_template("interactions.html", result=None, current_lang=get_language())
    
    # Pill Identifier
    @app.route("/pill-identify", methods=["GET", "POST"])
    def pill_identify():
        if request.method == "POST":
            if "image" not in request.files:
                flash("No image file")
                return redirect(url_for("pill_identify"))
            
            file = request.files["image"]
            if file.filename:
                filename = secure_filename(file.filename)
                saved_path = UPLOAD_DIR / filename
                file.save(saved_path)
                
                # Get all medicines for matching
                all_medicines = _fetch_all_medicine_names()
                medicine_data = [_fetch_medicine_by_id(mid) for mid, _ in all_medicines if _fetch_medicine_by_id(mid)]
                
                matches = identify_pill_from_image(str(saved_path), medicine_data)
                
                return render_template("pill_identify.html", matches=matches, image_path=f"uploads/{filename}", current_lang=get_language())
        
        return render_template("pill_identify.html", matches=None, image_path=None, current_lang=get_language())
    
    # Chatbot
    @app.route("/chatbot", methods=["GET", "POST"])
    def chatbot():
        if request.method == "POST":
            message = request.form.get("message", "").strip()
            if not message:
                flash("Please enter a message")
                return redirect(url_for("chatbot"))
            
            # Get context if viewing a medicine
            context = None
            if "current_medicine" in session:
                context = session["current_medicine"]
            
            # Try Groq first (free), then OpenAI
            api_key = os.environ.get("GROQ_API_KEY") or os.environ.get("OPENAI_API_KEY")
            # Use Groq if GROQ_API_KEY is set, otherwise fallback
            api_provider = "groq" if os.environ.get("GROQ_API_KEY") else "openai" if os.environ.get("OPENAI_API_KEY") else "groq"
            from features.chatbot import MedicineChatbot
            chatbot = MedicineChatbot(api_key=api_key, api_provider=api_provider)
            response = chatbot.get_response(message, context)
            
            return render_template("chatbot.html", response=response, current_lang=get_language())
        
        return render_template("chatbot.html", response=None, current_lang=get_language())
    
    # Language selector
    @app.route("/set-language/<lang>")
    def set_language(lang):
        if lang in SUPPORTED_LANGUAGES:
            session["language"] = lang
            flash(f"Language changed to {SUPPORTED_LANGUAGES[lang]}")
        return redirect(request.referrer or url_for("index"))

    return app


def _ensure_dirs() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _configure_tesseract_on_windows() -> None:
    # Try to locate tesseract on Windows if not in PATH
    if os.name == "nt":
        common_paths = [
            r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
            r"C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe",
        ]
        for path in common_paths:
            if Path(path).exists():
                pytesseract.pytesseract.tesseract_cmd = path
                break


def _init_db() -> None:
    if DB_PATH.exists():
        return

    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV not found at {CSV_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE medicines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medicine_name TEXT,
            composition TEXT,
            uses TEXT,
            side_effects TEXT,
            image_url TEXT,
            manufacturer TEXT,
            excellent_review_pct REAL,
            average_review_pct REAL,
            poor_review_pct REAL
        );
        """
    )

    import csv

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            rows.append(
                (
                    row.get("Medicine Name", ""),
                    row.get("Composition", ""),
                    row.get("Uses", ""),
                    row.get("Side_effects", ""),
                    row.get("Image URL", ""),
                    row.get("Manufacturer", ""),
                    _to_float(row.get("Excellent Review %")),
                    _to_float(row.get("Average Review %")),
                    _to_float(row.get("Poor Review %")),
                )
            )

    cur.executemany(
        """
        INSERT INTO medicines (
            medicine_name, composition, uses, side_effects, image_url,
            manufacturer, excellent_review_pct, average_review_pct, poor_review_pct
        ) VALUES (?,?,?,?,?,?,?,?,?);
        """,
        rows,
    )

    conn.commit()
    conn.close()


def _to_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(str(value).strip())
    except Exception:
        return None


def _extract_text_from_image(image_path: Path) -> str:
    image = Image.open(image_path)
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")

    # Basic normalization
    image = ImageOps.exif_transpose(image)  # auto-rotate if EXIF says so
    image = image.convert("L")  # grayscale

    # Resize up to help OCR on small text (cap large images)
    max_w = 1600
    if image.width < 800:
        scale = min(2.0, max_w / max(1, image.width))
        image = image.resize((int(image.width * scale), int(image.height * scale)), Image.BICUBIC)
    elif image.width > max_w:
        scale = max_w / image.width
        image = image.resize((int(image.width * scale), int(image.height * scale)), Image.BICUBIC)

    # Generate variants
    variants = []
    base = image.filter(ImageFilter.MedianFilter(size=3))
    variants.append(("base", base))
    variants.append(("sharpen", base.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))))
    # Binarize
    bw = base.point(lambda p: 255 if p > 170 else 0)
    variants.append(("binary170", bw))
    bw2 = base.point(lambda p: 255 if p > 140 else 0)
    variants.append(("binary140", bw2))

    # Try with OpenCV if available (adaptive threshold)
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
        np_img = np.array(base)
        cv_bin = cv2.adaptiveThreshold(np_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 5)
        variants.append(("cv_adaptive", Image.fromarray(cv_bin)))
    except Exception:
        pass

    # Tesseract configs to try
    configs = [
        "--oem 3 --psm 6",
        "--oem 3 --psm 7",
        "--oem 3 --psm 11",
    ]

    # Restrict to common package characters
    whitelist = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-+()/%.,\n "
    configs = [cfg + f" -c tessedit_char_whitelist={whitelist}" for cfg in configs]

    best_text = ""
    best_score = -1

    for _vname, vimg in variants:
        for cfg in configs:
            try:
                candidate = pytesseract.image_to_string(vimg, config=cfg)
            except Exception:
                continue
            text = (candidate or "").strip()
            # Score by number of alnum characters (rough proxy for usable text)
            score = sum(ch.isalnum() for ch in text)
            if score > best_score:
                best_score = score
                best_text = text

    return best_text


def _extract_heading_from_image(image_path: Path) -> Optional[str]:
    """
    Extract the text line that appears to be the largest "heading" based on
    bounding box height from Tesseract's layout output.
    """
    try:
        image = Image.open(image_path)
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        image = ImageOps.exif_transpose(image).convert("L")

        max_w = 1600
        if image.width < 800:
            scale = min(2.0, max_w / max(1, image.width))
            image = image.resize((int(image.width * scale), int(image.height * scale)), Image.BICUBIC)
        elif image.width > max_w:
            scale = max_w / image.width
            image = image.resize((int(image.width * scale), int(image.height * scale)), Image.BICUBIC)

        base = image.filter(ImageFilter.MedianFilter(size=3))

        # Use tesseract data output to get word-level boxes
        data = pytesseract.image_to_data(base, config="--oem 3 --psm 6", output_type=pytesseract.Output.DICT)  # type: ignore
        n = len(data.get("text", []))
        if n == 0:
            return None

        # Group words by line (block_num, par_num, line_num)
        from collections import defaultdict

        line_words: Dict[Tuple[int, int, int], List[Tuple[int, str]]] = defaultdict(list)
        for i in range(n):
            txt = (data["text"][i] or "").strip()
            conf = int(data.get("conf", ["-1"])[i]) if str(data.get("conf", ["-1"])[i]).isdigit() else -1
            if not txt:
                continue
            h = int(data.get("height", [0])[i] or 0)
            key = (
                int(data.get("block_num", [0])[i] or 0),
                int(data.get("par_num", [0])[i] or 0),
                int(data.get("line_num", [0])[i] or 0),
            )
            # Store (height, word)
            line_words[key].append((h, txt))

        if not line_words:
            return None

        # Score each line by max word height and average height as tiebreaker
        def line_score(words: List[Tuple[int, str]]) -> Tuple[int, float, int]:
            heights = [h for h, _ in words]
            return (max(heights), sum(heights) / max(1, len(heights)), len(heights))

        best_line = None
        best_metric: Tuple[int, float, int] = (-1, -1.0, -1)
        for key, words in line_words.items():
            metric = line_score(words)
            if metric > best_metric:
                best_metric = metric
                best_line = words

        if not best_line:
            return None

        # Reconstruct the heading text from that line (keep original order by height not reliable, so rely on index order via enumerate)
        heading = " ".join(word for _, word in best_line)
        heading = heading.strip()
        return heading or None
    except Exception:
        return None


def _fetch_all_medicine_names() -> List[Tuple[int, str]]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, medicine_name FROM medicines WHERE medicine_name IS NOT NULL AND medicine_name != '';")
    rows = cur.fetchall()
    conn.close()
    return [(r[0], r[1]) for r in rows]


def _fetch_medicine_by_id(mid: int) -> Optional[Dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM medicines WHERE id = ?;", (mid,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)


def _find_best_match(extracted_text: str) -> Tuple[Optional[Dict], List[Tuple[str, float]]]:
    names = _fetch_all_medicine_names()
    candidates: List[Tuple[str, float]] = []
    best_id: Optional[int] = None
    best_score: float = -1

    if RAPIDFUZZ_AVAILABLE:
        # Use RapidFuzz for better matching
        # case-insensitive: map lowercase name -> (id, original)
        choices = {name.lower(): (mid, name) for (mid, name) in names}
        query = extracted_text.lower()
        results = rapid_process.extract(query, choices.keys(), scorer=fuzz.token_set_ratio, limit=5)
        for lname, score, _ in results:
            mid, original = choices[lname]
            candidates.append((original, float(score)))
            if score > best_score:
                best_score = float(score)
                best_id = mid
    else:
        # Fallback: simple substring match scoring
        text_lower = extracted_text.lower()
        for mid, name in names:
            name_lower = name.lower()
            score = 0.0
            if name_lower in text_lower:
                score = 100.0
            else:
                # partial score by overlapping words
                name_tokens = set(name_lower.split())
                text_tokens = set(text_lower.split())
                overlap = len(name_tokens & text_tokens)
                score = 100.0 * overlap / max(1, len(name_tokens))
            candidates.append((name, score))
            if score > best_score:
                best_score = score
                best_id = mid

        candidates = sorted(candidates, key=lambda x: x[1], reverse=True)[:5]

    match = _fetch_medicine_by_id(best_id) if best_id is not None else None
    return match, candidates


def _compute_match_score(a: str, b: str) -> float:
    """Return a 0..100 similarity score between two strings."""
    if not a or not b:
        return 0.0
    if RAPIDFUZZ_AVAILABLE:
        return float(fuzz.token_set_ratio(a.lower(), b.lower()))
    # Fallback: simple token overlap percentage
    a_tokens = set(a.lower().split())
    b_tokens = set(b.lower().split())
    if not a_tokens or not b_tokens:
        return 0.0
    overlap = len(a_tokens & b_tokens)
    return 100.0 * overlap / max(1, len(b_tokens))


if __name__ == "__main__":
    _init_db()
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)


