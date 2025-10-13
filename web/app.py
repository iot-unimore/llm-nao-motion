from flask import Flask, render_template, request, redirect, url_for, session
from schema import db, User, Response
import random
from functools import wraps
import os
import glob

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = "supersecretkey"

db.init_app(app)

with app.app_context():
    db.create_all()


actions_code = [
    "arm_circles",
    "cheer_up",
    "clapping",
    "hands_up",
    "hand_shaking",
    "hand_waving",
    "kick_something",
    "nod_head",
    "pickup",
    "point_to_something",
    "salute",
    "shake_head",
    "sitting_down",
    "throw",
    "walking_towards",
]

actions_translations = {
    "arm_circles": {"en": "Arm Circles", "it": "Cerchi con le braccia"},
    "cheer_up": {"en": "Cheer Up", "it": "Rallegrarsi"},
    "clapping": {"en": "Clapping", "it": "Applaudire"},
    "hands_up": {"en": "Hands Up", "it": "Mani in alto"},
    "hand_shaking": {"en": "Hand Shaking", "it": "Stretta di mano"},
    "hand_waving": {"en": "Hand Waving", "it": "Salutare con la mano"},
    "kick_something": {"en": "Kick Something", "it": "Calciare qualcosa"},
    "nod_head": {"en": "Nod Head", "it": "Annuire con la testa"},
    "pickup": {"en": "Pickup", "it": "Raccogliere qualcosa"},
    "point_to_something": {"en": "Point To Something", "it": "Indicare qualcosa"},
    "salute": {"en": "Salute", "it": "Saluto militare"},
    "shake_head": {"en": "Shake Head", "it": "Scuotere la testa"},
    "sitting_down": {"en": "Sitting Down", "it": "Sedersi"},
    "throw": {"en": "Throw", "it": "Lanciare qualcosa"},
    "walking_towards": {"en": "Walking Towards", "it": "Camminare in avanti"},
}


def code2str(code):
    lang = session.get("lang", "en")
    return actions_translations[code][lang]


def str2code(string):
    lang = session.get("lang", "en")
    
    for code, translation in actions_translations.items():
        if translation[lang].lower() == string.lower():
            return code
    
    return string.replace(" ", "_").lower()


def getVideos(n, action=None, expert=False, shots=-1):
    folder = []
    root_dir = "static/videos"

    if expert:
        folders = ["Expert"]
    else:
        match shots:
            case -1:
                folders = ["LLM"]
            case 0:
                folders = ["LLM", "ZeroShot_videos"]
            case 1:
                folders = ["LLM", "OneShot_videos"]
            case _:
                assert False, "Invalid shots value. It should be -1, 0, or 1."

    all_videos = glob.glob(
        os.path.join(*folders, "**/*.mov"), recursive=True, root_dir=root_dir
    )

    if not action:
        return random.sample(all_videos, n)

    else:
        action_videos = [video for video in all_videos if action in video]
        if len(action_videos) < n:
            return action_videos
        else:
            return random.sample(action_videos, n)


def getMultipleVideoSingleAction(avoid_actions=[]):

    action_possible = list(set(actions_code) - set(avoid_actions))
    if len(action_possible) == 0:
        return [], None

    action = random.choice(action_possible)

    shots = random.choice([0, 1])

    videos = getVideos(4, action, shots=shots)
    return videos, code2str(action)


def getSingleVideoMultipleAction():
    video = getVideos(1)[0]
    for action in actions_code:
        if action in video:
            break

    actions = random.sample(actions_code, 4)
    if action not in actions:
        actions = actions[1:] + [action]

    actions = [code2str(a) for a in actions]

    return str(video), actions


def getSingleAndExpertVideo():
    video = getVideos(1)[0]
    for action in actions_code:
        if action in video:
            break

    expert_video = getVideos(1, action, expert=True)[0]
    videos = [video, expert_video]
    random.shuffle(videos)
    return videos, code2str(action)


def target_page(counta):
    if counta < 9:
        return "question1"
    elif counta < 24:
        return "question2"
    elif counta < 34:
        return "question3"
    elif counta < 35:
        return "index"
    else:
        return random.choice(
            [
                "question1",
                "question3",
            ]
        )


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("index"))
        return f(*args, **kwargs)

    return decorated_function


@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("index"))


@app.route("/", methods=["GET", "POST"])
def index():
    counta = (
        User.get_answer_count_for_user(session["username"])
        if "username" in session
        else 0
    )
    if request.method == "POST":
        username = request.form["username"].strip()
        if username:
            session["username"] = username
            # Create user if not exists
            user = User.query.filter_by(username=username).first()
            if not user:
                new_user = User(username=username)
                db.session.add(new_user)
                db.session.commit()
            return redirect(url_for("index"))

    return render_template(
        "index.html",
        lang=session.get("lang", "en"),
        answer_count=counta,
        cta_text="Start!" if session.get("lang", "en") == "en" else "Inizia!" if counta == 0 else "Continue!" if session.get("lang", "en") == "en" else "Continua!",
        cta_link=target_page(counta),
        completed=counta >= 30,
    )


@app.route("/q1", methods=["GET", "POST"])
@login_required
def question1():
    # identify the action in the video between a set of actions
    counta = (
        User.get_answer_count_for_user(session["username"])
        if "username" in session
        else 0
    )
    if request.method == "POST":
        selected_action = request.form.get("identified_action")
        actions = request.form.get("actions")
        video = request.form.get("video")
        if selected_action:
            response = Response(
                username=session["username"],
                question="classify_action",
                answer=str2code(selected_action),
                question_action=",".join(list(map(str2code, actions.split(",")))),
                question_video=video,
            )
            db.session.add(response)
            db.session.commit()

            User.add(session["username"], "classify_action")

        return redirect(url_for(target_page(counta)))

    elif request.method == "GET":
        video, actions = getSingleVideoMultipleAction()

        return render_template(
            "q1.html",
            lang=session.get("lang", "en"),
            answer_count=counta,
            completed=counta >= 35,
            video=video,
            actions=actions,
        )


@app.route("/q2", methods=["GET", "POST"])
@login_required
def question2():
    counta = (
        User.get_answer_count_for_user(session["username"])
        if "username" in session
        else 0
    )

    # select the best video = model to do the action
    if request.method == "POST":
        selected_video = request.form.get("best_video")
        action = request.form.get("action")
        videos = request.form.get("videos")
        if selected_video:
            response = Response(
                username=session["username"],
                question="select_best_video",
                question_action=str2code(action),
                question_video=str(videos),
                answer=selected_video,
            )

            db.session.add(response)
            db.session.commit()

            User.add_action(session["username"], str2code(action))

        return redirect(url_for(target_page(counta)))
    elif request.method == "GET":
        videos, action = getMultipleVideoSingleAction(
            avoid_actions=User.get_action_selected_for_user(
                session["username"], "select_best_video"
            )
        )
        print(videos, action)
        return render_template(
            "q2.html",
            lang=session.get("lang", "en"),
            answer_count=counta,
            completed=action == None,
            videos=videos,
            action=action,
        )


@app.route("/q3", methods=["GET", "POST"])
@login_required
def question3():
    counta = (
        User.get_answer_count_for_user(session["username"])
        if "username" in session
        else 0
    )

    # select the best video = model to do the action
    if request.method == "POST":
        expert_like = request.form.get("expert_like")
        action = request.form.get("action")
        videos = request.form.get("videos")
        if expert_like:
            response = Response(
                username=session["username"],
                question="expert_like",
                question_action=str2code(action),
                question_video=str(videos),
                answer=expert_like,
            )
            db.session.add(response)
            db.session.commit()

            User.add(session["username"], "expert_like")
        return redirect(url_for(target_page(counta)))
    elif request.method == "GET":
        videos, action = getSingleAndExpertVideo()

        print(videos, action)
        return render_template(
            "q3.html",
            lang=session.get("lang", "en"),
            answer_count=counta,
            completed=counta >= 35,
            videos=videos,
            action=action,
        )


@app.route("/change_lang", methods=["POST"])
def change_lang():
    selected_lang = request.form.get("lang", "en")
    session["lang"] = selected_lang
    return redirect(request.referrer or url_for("index"))


@app.route("/en")
def set_lang_en():
    session["lang"] = "en"
    return redirect(request.referrer or url_for("index"))


@app.route("/it")
def set_lang_it():
    session["lang"] = "it"
    return redirect(request.referrer or url_for("index"))
