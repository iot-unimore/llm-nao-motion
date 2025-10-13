from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

class User(db.Model):
    username = db.Column(db.String(50), unique=True, nullable=False, primary_key=True)
    action_best_videos = db.Column(db.String(255), nullable=True)  # every time a user selects a video, the action will be added to this list
    # Relationship to Response
    n_responses_classify_action = db.Column(db.Integer, default=0)
    n_responses_like_expert = db.Column(db.Integer, default=0)
    responses = db.relationship('Response', backref='user_obj', lazy=True)
    
    @staticmethod
    def _get_answer_count(user):
        action_best_videos_count = len(user.action_best_videos.split(',')) if user.action_best_videos else 0
        return user.n_responses_classify_action + user.n_responses_like_expert + action_best_videos_count
    
    @staticmethod
    def get_answer_count_for_user(username):
        user = User.query.filter_by(username=username).first()
        if not user:
            return 0
        return User._get_answer_count(user)
    
    @staticmethod
    def add(username, question):
        user = User.query.filter_by(username=username).first()
        if not user:
            return
        if question == "classify_action":
            user.n_responses_classify_action += 1
        elif question == "expert_like":
            user.n_responses_like_expert += 1
        else:
            raise ValueError("Invalid question type")
        
        db.session.commit()
        
        return User._get_answer_count(user)
        

    @staticmethod
    def add_action(username, action):
        user = User.query.filter_by(username=username).first()
        if user:
            if user.action_best_videos:
                user.action_best_videos += "," + action
            else:
                user.action_best_videos = action
            db.session.commit()
        
        return User._get_answer_count(user)
    
    @staticmethod
    def get_action_selected_for_user(username, question):
        user = User.query.filter_by(username=username).first()
        return user.action_best_videos.split(',') if user and user.action_best_videos else []
    
class Response(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), db.ForeignKey('user.username'), nullable=False)
    question = db.Column(db.String(50), nullable=False)
    question_action = db.Column(db.String(255), nullable=False)
    question_video = db.Column(db.String(255), nullable=True)
    answer = db.Column(db.String(255), nullable=False)

    @staticmethod
    def get_answer_count_for_user(username):
        return Response.query.filter_by(username=username).count()
    
    @staticmethod
    def get_action_selected_for_user(username, question):
        return [a[0] for a in (db.session.query(Response.question_action)
            .filter_by(username=username, question=question)
            .distinct()
            .all())]
