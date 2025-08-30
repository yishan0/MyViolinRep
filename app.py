from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import json
import os
import time
import os
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests
import requests as http_requests

app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///myviolinrep.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# File upload configuration
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'mp4', 'avi', 'mov', 'mp3', 'wav', 'pdf', 'doc', 'docx', 'txt'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Google OAuth Configuration
GOOGLE_CLIENT_ID = "your-google-client-id.apps.googleusercontent.com"  # Replace with your actual client ID
GOOGLE_CLIENT_SECRET = "your-google-client-secret"  # Replace with your actual client secret
GOOGLE_REDIRECT_URI = "http://localhost:5000/google-callback"  # Update for production

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    bio = db.Column(db.Text)
    avatar = db.Column(db.String(200))
    country = db.Column(db.String(100))
    currently_practicing = db.Column(db.String(200))
    join_date = db.Column(db.DateTime, default=datetime.utcnow)
    contribution_score = db.Column(db.Integer, default=0)
    forum_score = db.Column(db.Integer, default=0)
    ratings = db.relationship('Rating', backref='user', lazy=True)
    comments = db.relationship('Comment', backref='user', lazy=True)
    submissions = db.relationship('Piece', backref='submitter', lazy=True)
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy=True)
    received_messages = db.relationship('Message', foreign_keys='Message.recipient_id', backref='recipient', lazy=True)
    favorites = db.relationship('Favorite', backref='user', lazy=True)


class Piece(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    composer = db.Column(db.String(100), nullable=False)
    era = db.Column(db.String(50), nullable=False)
    genre = db.Column(db.String(100), nullable=False)
    opus = db.Column(db.String(100))
    length = db.Column(db.String(50))
    cover_image = db.Column(db.String(200))
    recording_link = db.Column(db.String(500))
    performance_links = db.Column(db.Text)  # JSON string
    technical_tags = db.Column(db.Text)  # JSON string
    difficulty_avg = db.Column(db.Float, default=0.0)
    total_ratings = db.Column(db.Integer, default=0)
    submitter_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    is_approved = db.Column(db.Boolean, default=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.Text)
    ratings = db.relationship('Rating', backref='piece', lazy=True)
    comments = db.relationship('Comment', backref='piece', lazy=True)
    favorites = db.relationship('Favorite', backref='piece', lazy=True)

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    piece_id = db.Column(db.Integer, db.ForeignKey('piece.id'), nullable=False)
    difficulty_rating = db.Column(db.Integer, nullable=False)
    date_rated = db.Column(db.DateTime, default=datetime.utcnow)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    piece_id = db.Column(db.Integer, db.ForeignKey('piece.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    tags = db.Column(db.Text)  # JSON string for tags
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)  # For replies
    likes = db.relationship('CommentLike', backref='comment', lazy=True)
    replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[id]), lazy=True)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_sent = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    room = db.Column(db.String(100), default='general')  # For community chat rooms

class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    piece_id = db.Column(db.Integer, db.ForeignKey('piece.id'), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

class CommentLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=False)
    date_liked = db.Column(db.DateTime, default=datetime.utcnow)



@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))



# Custom Jinja2 filter
@app.template_filter('from_json')
def from_json(value):
    if value:
        try:
            result = json.loads(value)
            # If result is a string, don't iterate over characters
            if isinstance(result, str):
                return [result] if result.strip() else []
            # If result is a list, filter out empty strings
            elif isinstance(result, list):
                return [item for item in result if item and str(item).strip()]
            else:
                return []
        except:
            return []
    return []

@app.template_filter('get_difficulty_level')
def get_difficulty_level(score):
    if score <= 3:
        return "Beginner"
    elif score <= 7:
        return "Intermediate"
    else:
        return "Advanced"

# Routes
@app.route('/')
def index():
    featured_piece = Piece.query.filter_by(is_approved=True).first()
    recent_pieces = Piece.query.filter_by(is_approved=True).order_by(Piece.date_added.desc()).limit(3).all()
    top_users = User.query.order_by(User.contribution_score.desc()).limit(5).all()
    
    return render_template('index.html', 
                         featured_piece=featured_piece,
                         recent_pieces=recent_pieces,
                         top_users=top_users)

def find_similar_pieces(piece, limit=6):
    """Find similar pieces based on composer, era, genre, and difficulty"""
    similar_pieces = []
    
    # Get pieces by same composer (highest priority)
    same_composer = Piece.query.filter(
        Piece.composer == piece.composer,
        Piece.id != piece.id,
        Piece.is_approved == True
    ).limit(2).all()
    similar_pieces.extend(same_composer)
    
    # Get pieces by same era
    same_era = Piece.query.filter(
        Piece.era == piece.era,
        Piece.id != piece.id,
        Piece.is_approved == True,
        ~Piece.id.in_([p.id for p in similar_pieces])
    ).limit(2).all()
    similar_pieces.extend(same_era)
    
    # Get pieces by same genre
    same_genre = Piece.query.filter(
        Piece.genre == piece.genre,
        Piece.id != piece.id,
        Piece.is_approved == True,
        ~Piece.id.in_([p.id for p in similar_pieces])
    ).limit(2).all()
    similar_pieces.extend(same_genre)
    
    # If we don't have enough, fill with random approved pieces
    if len(similar_pieces) < limit:
        remaining = limit - len(similar_pieces)
        random_pieces = Piece.query.filter(
            Piece.id != piece.id,
            Piece.is_approved == True,
            ~Piece.id.in_([p.id for p in similar_pieces])
        ).order_by(db.func.random()).limit(remaining).all()
        similar_pieces.extend(random_pieces)
    
    return similar_pieces[:limit]

@app.route('/library')
def library():
    page = request.args.get('page', 1, type=int)
    composer = request.args.get('composer', '')
    era = request.args.get('era', '')
    genre = request.args.get('genre', '')
    difficulty = request.args.get('difficulty', '')
    

    query = Piece.query.filter_by(is_approved=True)
    
    if composer:
        query = query.filter(Piece.composer.ilike(f'%{composer}%'))
    if era:
        query = query.filter_by(era=era)
    if genre:
        query = query.filter_by(genre=genre)
    if difficulty:
        if difficulty == '9-10':
            query = query.filter(Piece.difficulty_avg >= 9, Piece.difficulty_avg <= 10)
        elif difficulty == '8':
            query = query.filter(Piece.difficulty_avg >= 7.5, Piece.difficulty_avg < 8.5)
        elif difficulty == '7':
            query = query.filter(Piece.difficulty_avg >= 6.5, Piece.difficulty_avg < 7.5)
        elif difficulty == '6':
            query = query.filter(Piece.difficulty_avg >= 5.5, Piece.difficulty_avg < 6.5)
        elif difficulty == '5':
            query = query.filter(Piece.difficulty_avg >= 4.5, Piece.difficulty_avg < 5.5)
        elif difficulty == '3-4':
            query = query.filter(Piece.difficulty_avg >= 2.5, Piece.difficulty_avg < 4.5)
        elif difficulty == '2':
            query = query.filter(Piece.difficulty_avg >= 1.5, Piece.difficulty_avg < 2.5)
        elif difficulty == '0-1':
            query = query.filter(db.or_(Piece.difficulty_avg == None, Piece.difficulty_avg < 1.5))
    
    pieces = query.order_by(Piece.title).paginate(page=page, per_page=12, error_out=False)
    
    # Get all unique composers from approved pieces for the filter dropdown
    all_composers = db.session.query(Piece.composer).filter_by(is_approved=True).distinct().order_by(Piece.composer).all()
    composers = [composer[0] for composer in all_composers]
    
    return render_template('library.html', pieces=pieces, composers=composers)

@app.route('/piece/<int:piece_id>')
def piece_detail(piece_id):
    piece = Piece.query.get_or_404(piece_id)
    comments = Comment.query.filter_by(piece_id=piece_id, parent_id=None).order_by(Comment.date_posted.desc()).all()
    user_rating = None
    comment_likes = {}
    user_likes = {}
    
    if current_user.is_authenticated:
        user_rating = Rating.query.filter_by(user_id=current_user.id, piece_id=piece_id).first()
        
        # Get like counts and user's likes for each comment
        for comment in comments:
            like_count = CommentLike.query.filter_by(comment_id=comment.id).count()
            user_liked = CommentLike.query.filter_by(user_id=current_user.id, comment_id=comment.id).first() is not None
            comment_likes[comment.id] = like_count
            user_likes[comment.id] = user_liked
    else:
        # For anonymous users, just get like counts
        for comment in comments:
            like_count = CommentLike.query.filter_by(comment_id=comment.id).count()
            comment_likes[comment.id] = like_count
            user_likes[comment.id] = False
    
    # Get similar pieces
    similar_pieces = find_similar_pieces(piece)
    
    return render_template('piece_detail.html', 
                         piece=piece, 
                         comments=comments,
                         user_rating=user_rating,
                         comment_likes=comment_likes,
                         user_likes=user_likes,
                         similar_pieces=similar_pieces)

@app.route('/rate_piece', methods=['POST'])
@login_required
def rate_piece():
    data = request.get_json()
    piece_id = data['piece_id']
    rating_value = data['rating']
    
    existing_rating = Rating.query.filter_by(user_id=current_user.id, piece_id=piece_id).first()
    is_new_rating = existing_rating is None
    
    if existing_rating:
        existing_rating.difficulty_rating = rating_value
        existing_rating.date_rated = datetime.utcnow()
    else:
        new_rating = Rating(user_id=current_user.id, piece_id=piece_id, difficulty_rating=rating_value)
        db.session.add(new_rating)
        # Increment user contribution score for new rating
        current_user.contribution_score += 1
    
    # Update piece average
    piece = Piece.query.get(piece_id)
    ratings = Rating.query.filter_by(piece_id=piece_id).all()
    if ratings:
        piece.difficulty_avg = sum(r.difficulty_rating for r in ratings) / len(ratings)
        piece.total_ratings = len(ratings)
    
    db.session.commit()
    
    return jsonify({'success': True, 'new_average': piece.difficulty_avg, 'is_new_rating': is_new_rating})

@app.route('/add_comment', methods=['POST'])
@login_required
def add_comment():
    data = request.get_json()
    piece_id = data['piece_id']
    content = data['content']
    tags = data.get('tags', [])
    
    comment = Comment(
        user_id=current_user.id,
        piece_id=piece_id,
        content=content,
        tags=json.dumps(tags)
    )
    
    db.session.add(comment)
    current_user.forum_score += 1
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/add_reply', methods=['POST'])
@login_required
def add_reply():
    data = request.get_json()
    parent_id = data['parent_id']
    content = data['content'].strip()
    
    if not content:
        return jsonify({'success': False, 'message': 'Reply content cannot be empty'})
    
    # Get the parent comment to ensure it exists and get the piece_id
    parent_comment = Comment.query.get_or_404(parent_id)
    
    reply = Comment(
        user_id=current_user.id,
        piece_id=parent_comment.piece_id,
        content=content,
        parent_id=parent_id
    )
    
    db.session.add(reply)
    current_user.forum_score += 1
    db.session.commit()
    
    return jsonify({
        'success': True,
        'reply': {
            'id': reply.id,
            'content': reply.content,
            'author': current_user.username,
            'date_posted': reply.date_posted.strftime('%B %d, %Y at %I:%M %p')
        }
    })

@app.route('/like_comment', methods=['POST'])
@login_required
def like_comment():
    data = request.get_json()
    comment_id = data['comment_id']
    
    # Check if user already liked this comment
    existing_like = CommentLike.query.filter_by(user_id=current_user.id, comment_id=comment_id).first()
    
    if existing_like:
        # Unlike the comment
        db.session.delete(existing_like)
        action = 'unliked'
        
        # Remove point from comment author
        comment = Comment.query.get(comment_id)
        if comment and comment.user:
            comment.user.forum_score = max(0, comment.user.forum_score - 1)
    else:
        # Like the comment
        new_like = CommentLike(user_id=current_user.id, comment_id=comment_id)
        db.session.add(new_like)
        action = 'liked'
        
        # Add point to comment author (upvote = 1 point)
        comment = Comment.query.get(comment_id)
        if comment and comment.user:
            comment.user.forum_score += 1
    
    db.session.commit()
    
    # Get updated like count
    like_count = CommentLike.query.filter_by(comment_id=comment_id).count()
    
    return jsonify({'success': True, 'action': action, 'like_count': like_count})

@app.route('/submit_piece', methods=['GET', 'POST'])
@login_required
def submit_piece():
    if request.method == 'POST':
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
            cover_image_url = data.get('cover_image', '')
            # Ensure cover_image_url is a string, not a dict
            if isinstance(cover_image_url, dict):
                cover_image_url = ''
        else:
            # Handle multipart form data with file upload
            data = request.form.to_dict()
            cover_image_url = ''
            
            # Handle file upload
            if 'cover_image' in request.files:
                file = request.files['cover_image']
                if file and file.filename and allowed_file(file.filename):
                    # Create uploads directory if it doesn't exist
                    upload_dir = os.path.join('static', 'uploads', 'pieces')
                    os.makedirs(upload_dir, exist_ok=True)
                    
                    # Generate unique filename
                    filename = secure_filename(file.filename)
                    unique_filename = f"{int(time.time())}_{filename}"
                    file_path = os.path.join(upload_dir, unique_filename)
                    
                    # Save file
                    file.save(file_path)
                    cover_image_url = f"/static/uploads/pieces/{unique_filename}"
        
        # Ensure performance_links is always a list
        performance_links = data.get('performance_links', [])
        if isinstance(performance_links, str):
            # If it's a string, split by newlines and filter empty ones
            performance_links = [link.strip() for link in performance_links.split('\n') if link.strip()]
        elif not isinstance(performance_links, list):
            performance_links = []
        
        # Handle technical_tags - convert from string if needed
        technical_tags = data.get('technical_tags', [])
        if isinstance(technical_tags, str):
            try:
                technical_tags = json.loads(technical_tags)
            except:
                technical_tags = []
        
        piece = Piece(
            title=data['title'],
            composer=data['composer'],
            era=data['era'],
            genre=data['genre'],
            opus=data.get('opus', ''),
            length=data.get('length', ''),
            recording_link=data.get('recording_link', ''),
            performance_links=json.dumps(performance_links),
            technical_tags=json.dumps(technical_tags),
            description=data.get('description', ''),
            cover_image=cover_image_url,
            submitter_id=current_user.id
        )
        
        db.session.add(piece)
        current_user.contribution_score += 10
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Piece submitted for approval!'})
    
    return render_template('submit_piece.html')

@app.route('/favorite_piece', methods=['POST'])
@login_required
def favorite_piece():
    data = request.get_json()
    piece_id = data['piece_id']
    
    existing_favorite = Favorite.query.filter_by(user_id=current_user.id, piece_id=piece_id).first()
    
    if existing_favorite:
        db.session.delete(existing_favorite)
        action = 'removed'
    else:
        new_favorite = Favorite(user_id=current_user.id, piece_id=piece_id)
        db.session.add(new_favorite)
        action = 'added'
    
    db.session.commit()
    return jsonify({'success': True, 'action': action})

@app.route('/leaderboard')
def leaderboard():

    top_contributors = User.query.order_by(User.contribution_score.desc()).limit(10).all()
    top_forum_users = User.query.order_by(User.forum_score.desc()).limit(10).all()
    
    return render_template('leaderboard.html', 
                         top_contributors=top_contributors,
                         top_forum_users=top_forum_users)

@app.route('/chat')
@login_required
def chat():
    return render_template('chat.html')

@app.route('/profile/<username>')
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    user_pieces = Piece.query.filter_by(submitter_id=user.id, is_approved=True).all()
    user_ratings = Rating.query.filter_by(user_id=user.id).all()
    user_comments = Comment.query.filter_by(user_id=user.id).all()
    user_favorites = Favorite.query.filter_by(user_id=user.id).all()
    
    # Get the actual piece data for favorites
    favorite_pieces = []
    for favorite in user_favorites:
        piece = Piece.query.get(favorite.piece_id)
        if piece and piece.is_approved:
            favorite_pieces.append(piece)

    return render_template('profile.html', 
                         user=user, 
                         user_pieces=user_pieces,
                         user_ratings=user_ratings,
                         user_comments=user_comments,
                         user_favorites=user_favorites,
                         favorite_pieces=favorite_pieces)

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    data = request.get_json()
    
    # Check if username is being changed and if it's already taken
    if 'username' in data and data['username'] != current_user.username:
        existing_user = User.query.filter_by(username=data['username']).first()
        if existing_user:
            return jsonify({'success': False, 'message': 'Username already taken'})
        current_user.username = data['username']
    
    # Update other fields
    if 'bio' in data:
        current_user.bio = data['bio'] if data['bio'] else None
    if 'country' in data:
        current_user.country = data['country'] if data['country'] else None
    if 'currently_practicing' in data:
        current_user.currently_practicing = data['currently_practicing'] if data['currently_practicing'] else None
    if 'avatar' in data:
        current_user.avatar = data['avatar'] if data['avatar'] else None
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'Profile updated successfully'})

@app.route('/upload_avatar', methods=['POST'])
@login_required
def upload_avatar():
    if 'avatar' not in request.files:
        return jsonify({'success': False, 'message': 'No file uploaded'})
    
    file = request.files['avatar']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'})
    
    if file:
        # Create uploads directory if it doesn't exist
        import os
        upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads', 'avatars')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        filename = f"avatar_{current_user.id}_{int(datetime.utcnow().timestamp())}.jpg"
        filepath = os.path.join(upload_dir, filename)
        
        # Save the file
        file.save(filepath)
        
        # Update user avatar path
        avatar_url = f"/static/uploads/avatars/{filename}"
        current_user.avatar = avatar_url
        db.session.commit()
        
        return jsonify({'success': True, 'avatar': avatar_url})
    
    return jsonify({'success': False, 'message': 'Upload failed'})

@app.route('/upload_chat_file', methods=['POST'])
@login_required
def upload_chat_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file uploaded'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'})
    
    if file and allowed_file(file.filename):
        # Create uploads directory if it doesn't exist
        import os
        upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads', 'chat')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{current_user.id}_{int(datetime.utcnow().timestamp())}{ext}"
        filepath = os.path.join(upload_dir, unique_filename)
        
        # Save the file
        file.save(filepath)
        
        # Return file URL
        file_url = f"/static/uploads/chat/{unique_filename}"
        return jsonify({
            'success': True, 
            'file_url': file_url,
            'filename': filename,
            'file_type': file.content_type
        })
    
    return jsonify({'success': False, 'message': 'Invalid file type'})

@app.route('/admin/upload_cover_image', methods=['POST'])
@login_required
def admin_upload_cover_image():
    if not current_user.username == 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    if 'cover_image' not in request.files:
        return jsonify({'success': False, 'message': 'No file uploaded'})
    
    file = request.files['cover_image']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'})
    
    if file and allowed_file(file.filename):
        # Create uploads directory if it doesn't exist
        import os
        upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads', 'pieces')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{int(datetime.utcnow().timestamp())}{ext}"
        filepath = os.path.join(upload_dir, unique_filename)
        
        # Save the file
        file.save(filepath)
        
        # Return file URL
        file_url = f"/static/uploads/pieces/{unique_filename}"
        return jsonify({
            'success': True, 
            'file_url': file_url,
            'filename': filename
        })
    
    return jsonify({'success': False, 'message': 'Invalid file type'})

@app.route('/get_emoji_list')
def get_emoji_list():
    # Return a list of common emojis
    emojis = [
        "😀", "😃", "😄", "😁", "😆", "😅", "😂", "🤣", "😊", "😇",
        "🙂", "🙃", "😉", "😌", "😍", "🥰", "😘", "😗", "😙", "😚",
        "😋", "😛", "😝", "😜", "🤪", "🤨", "🧐", "🤓", "😎", "🤩",
        "🥳", "😏", "😒", "😞", "😔", "😟", "😕", "🙁", "☹️", "😣",
        "😖", "😫", "😩", "🥺", "😢", "😭", "😤", "😠", "😡", "🤬",
        "🤯", "😳", "🥵", "🥶", "😱", "😨", "😰", "😥", "😓", "🤗",
        "🤔", "🤭", "🤫", "🤥", "😶", "😐", "😑", "😯", "😦", "😧",
        "😮", "😲", "🥱", "😴", "🤤", "😪", "😵", "🤐", "🥴", "🤢",
        "🤮", "🤧", "😷", "🤒", "🤕", "🤑", "🤠", "💩", "👻", "💀",
        "☠️", "👽", "👾", "🤖", "😺", "😸", "😹", "😻", "😼", "😽",
        "🙀", "😿", "😾", "🙈", "🙉", "🙊", "👶", "👧", "🧒", "👦",
        "👩", "🧑", "👨", "👵", "🧓", "👴", "👮", "🕵️", "👷", "👸",
        "🤴", "👳", "👲", "🧕", "🤵", "👰", "🤰", "🤱", "👼", "🎅",
        "🤶", "🧙", "🧚", "🧛", "🧜", "🧝", "🧞", "🧟", "🧌", "👹",
        "👺", "🤡", "👻", "👽", "👾", "🤖", "😀", "😃", "😄", "😁"
    ]
    return jsonify({'success': True, 'emojis': emojis})



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        user = User.query.filter_by(username=data['username']).first()
        
        if user and check_password_hash(user.password_hash, data['password']):
            login_user(user)
            return jsonify({'success': True, 'redirect': url_for('index')})
        else:
            return jsonify({'success': False, 'message': 'Invalid username or password'})
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json()
        
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'success': False, 'message': 'Username already exists'})
        
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'success': False, 'message': 'Email already registered'})
        
        user = User(
            username=data['username'],
            email=data['email'],
            password_hash=generate_password_hash(data['password']),
            bio=data.get('bio', ''),
            country=data.get('country', '')
        )
        
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return jsonify({'success': True, 'redirect': url_for('index')})
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Google OAuth routes
@app.route('/google-login')
def google_login():
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [GOOGLE_REDIRECT_URI]
            }
        },
        scopes=['openid', 'email', 'profile']
    )
    
    flow.redirect_uri = GOOGLE_REDIRECT_URI
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    
    session['state'] = state
    return redirect(authorization_url)

@app.route('/google-callback')
def google_callback():
    try:
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [GOOGLE_REDIRECT_URI]
                }
            },
            scopes=['openid', 'email', 'profile']
        )
        
        flow.redirect_uri = GOOGLE_REDIRECT_URI
        
        # Get authorization code from callback
        authorization_response = request.url
        flow.fetch_token(authorization_response=authorization_response)
        
        # Get user info from ID token
        id_info = id_token.verify_oauth2_token(
            flow.credentials.id_token, 
            requests.Request(), 
            GOOGLE_CLIENT_ID
        )
        
        # Extract user information
        google_id = id_info['sub']
        email = id_info['email']
        name = id_info.get('name', email.split('@')[0])
        
        # Check if user exists
        user = User.query.filter_by(email=email).first()
        
        if not user:
            # Create new user
            username = name
            counter = 1
            while User.query.filter_by(username=username).first():
                username = f"{name}{counter}"
                counter += 1
            
            user = User(
                username=username,
                email=email,
                password_hash='',  # No password for OAuth users
                bio=f'Joined via Google OAuth',
                country=''
            )
            db.session.add(user)
            db.session.commit()
        
        # Log in user
        login_user(user)
        return redirect(url_for('index'))
        
    except Exception as e:
        print(f"Google OAuth error: {e}")
        flash('Google login failed. Please try again.', 'error')
        return redirect(url_for('login'))

# Admin routes
@app.route('/admin/pending')
@login_required
def admin_pending():
    if not current_user.username == 'admin':  # Simple admin check
        return redirect(url_for('index'))
    
    pending_pieces = Piece.query.filter_by(is_approved=False).all()
    approved_count = Piece.query.filter_by(is_approved=True).count()
    total_users = User.query.count()
    total_pieces = Piece.query.count()
    
    return render_template('admin_pending.html', 
                         pending_pieces=pending_pieces,
                         approved_count=approved_count,
                         total_users=total_users,
                         total_pieces=total_pieces)

@app.route('/admin/approve/<int:piece_id>', methods=['POST'])
@login_required
def admin_approve(piece_id):
    if not current_user.username == 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    piece = Piece.query.get_or_404(piece_id)
    piece.is_approved = True
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/admin/reject/<int:piece_id>', methods=['POST'])
@login_required
def admin_reject(piece_id):
    if not current_user.username == 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    data = request.get_json()
    piece = Piece.query.get_or_404(piece_id)
    
    # Here you could send rejection email/notification
    db.session.delete(piece)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/admin/edit/<int:piece_id>', methods=['POST'])
@login_required
def admin_edit(piece_id):
    if not current_user.username == 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    data = request.get_json()
    piece = Piece.query.get_or_404(piece_id)
    
    # Update basic fields
    piece.title = data['title']
    piece.composer = data['composer']
    piece.era = data['era']
    piece.genre = data['genre']
    piece.opus = data.get('opus', '')
    piece.length = data.get('length', '')
    piece.description = data.get('description', '')
    piece.recording_link = data.get('recording_link', '')
    
    # Handle cover image update
    if 'cover_image' in data and data['cover_image']:
        piece.cover_image = data['cover_image']
    
    # Handle performance_links
    performance_links = data.get('performance_links', [])
    if isinstance(performance_links, str):
        performance_links = [link.strip() for link in performance_links.split('\n') if link.strip()]
    elif not isinstance(performance_links, list):
        performance_links = []
    piece.performance_links = json.dumps(performance_links)
    
    # Handle technical_tags - fix the parsing
    technical_tags = data.get('technical_tags', [])
    if isinstance(technical_tags, str):
        # If it's a comma-separated string, split it
        if ',' in technical_tags:
            technical_tags = [tag.strip() for tag in technical_tags.split(',') if tag.strip()]
        else:
            # Try to parse as JSON first
            try:
                technical_tags = json.loads(technical_tags)
            except:
                # If not JSON, treat as single tag
                technical_tags = [technical_tags.strip()] if technical_tags.strip() else []
    elif not isinstance(technical_tags, list):
        technical_tags = []
    piece.technical_tags = json.dumps(technical_tags)
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'Piece updated successfully!'})

@app.route('/admin/approve-all', methods=['POST'])
@login_required
def admin_approve_all():
    if not current_user.username == 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    pending_pieces = Piece.query.filter_by(is_approved=False).all()
    for piece in pending_pieces:
        piece.is_approved = True
    
    db.session.commit()
    return jsonify({'success': True, 'count': len(pending_pieces)})

@app.route('/admin/delete_message/<int:message_id>', methods=['POST'])
@login_required
def admin_delete_message(message_id):
    if not current_user.username == 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    message = Message.query.get_or_404(message_id)
    db.session.delete(message)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/edit_message', methods=['POST'])
@login_required
def edit_message():
    data = request.get_json()
    message_id = data.get('message_id')
    new_content = data.get('content', '').strip()

    if not message_id or not new_content:
        return jsonify({'success': False, 'message': 'Invalid data'})

    message = Message.query.get(message_id)
    if not message:
        return jsonify({'success': False, 'message': 'Message not found'})

    # Check if user can edit this message (own message only)
    if message.sender_id != current_user.id:
        return jsonify({'success': False, 'message': 'You can only edit your own messages'})

    try:
        # Update message content
        message.content = new_content
        db.session.commit()
        return jsonify({'success': True, 'message': 'Message updated'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error updating message'})

@app.route('/delete_message', methods=['POST'])
@login_required
def delete_user_message():
    data = request.get_json()
    message_id = data.get('message_id')

    if not message_id:
        return jsonify({'success': False, 'message': 'Invalid data'})

    message = Message.query.get(message_id)
    if not message:
        return jsonify({'success': False, 'message': 'Message not found'})
    
    # Check if user can delete this message (own message or admin)
    if message.sender_id != current_user.id and current_user.username != 'admin':
        return jsonify({'success': False, 'message': 'You can only delete your own messages'})
    
    try:
        db.session.delete(message)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Message deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error deleting message'})

@app.route('/delete_comment/<int:comment_id>', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    
    if comment.user_id != current_user.id and current_user.username != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    db.session.delete(comment)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/edit_comment/<int:comment_id>', methods=['POST'])
@login_required
def edit_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    
    if comment.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    data = request.get_json()
    comment.content = data['content']
    comment.tags = json.dumps(data.get('tags', []))
    
    db.session.commit()
    return jsonify({'success': True})

@app.route('/edit_reply/<int:reply_id>', methods=['POST'])
@login_required
def edit_reply(reply_id):
    reply = Comment.query.get_or_404(reply_id)
    
    # Check if user owns the reply
    if reply.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'You can only edit your own replies'})
    
    data = request.get_json()
    new_content = data['content'].strip()
    
    if not new_content:
        return jsonify({'success': False, 'message': 'Reply content cannot be empty'})
    
    reply.content = new_content
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/delete_reply/<int:reply_id>', methods=['POST'])
@login_required
def delete_reply(reply_id):
    reply = Comment.query.get_or_404(reply_id)
    
    # Check if user can delete this reply (own reply or admin)
    if reply.user_id != current_user.id and current_user.username != 'admin':
        return jsonify({'success': False, 'message': 'You can only delete your own replies'})
    
    try:
        db.session.delete(reply)
        if reply.user:
            reply.user.forum_score = max(0, reply.user.forum_score - 1)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error deleting reply'})

@app.route('/send_message', methods=['POST'])
@login_required
def send_message():
    data = request.get_json()
    content = data.get('content', '').strip()
    room = data.get('room', 'general')
    recipient = data.get('recipient')
    
    print(f"DEBUG: Received message - content: '{content}', room: '{room}', recipient: '{recipient}'")
    print(f"DEBUG: Content length: {len(content)}")
    print(f"DEBUG: Current user: {current_user.username}")
    
    if not content:
        return jsonify({'success': False, 'message': 'Message content is required'})
    
    if room == 'general':
        message = Message(
            sender_id=current_user.id,
            recipient_id=current_user.id,  # Self for general room
            content=content,
            room='general'
        )
    elif room.startswith('dm_'):
        # For DMs, extract recipient from room name
        try:
            usernames = room.split('_')[1:]
            if len(usernames) == 2:
                username1, username2 = usernames[0], usernames[1]
                
                # Ensure current user is one of the participants
                if current_user.username not in [username1, username2]:
                    return jsonify({'success': False, 'message': 'Unauthorized access to this chat'})
                
                # Get the other user's username
                other_username = username1 if current_user.username == username2 else username2
                other_user = User.query.filter_by(username=other_username).first()
                
                if not other_user:
                    return jsonify({'success': False, 'message': 'User not found'})
                
                message = Message(
                    sender_id=current_user.id,
                    recipient_id=other_user.id,
                    content=content,
                    room=room
                )
            else:
                return jsonify({'success': False, 'message': 'Invalid room format'})
        except (ValueError, IndexError):
            return jsonify({'success': False, 'message': 'Invalid room format'})
    else:
        # For other rooms (technique, repertoire, etc.)
        message = Message(
            sender_id=current_user.id,
            recipient_id=current_user.id,  # Self for other rooms
            content=content,
            room=room
        )
    
    print(f"DEBUG: About to save message - content: '{message.content}', room: '{message.room}'")
    
    db.session.add(message)
    db.session.commit()
    
    print(f"DEBUG: Message saved successfully with ID: {message.id}")
    
    return jsonify({'success': True})

@app.route('/get_messages/<room>')
@login_required
def get_messages(room):
    print(f"DEBUG: Getting messages for room: '{room}'")
    
    if room == 'general':
        messages = Message.query.filter_by(room='general').order_by(Message.date_sent.asc()).limit(50).all()
    elif room.startswith('dm_'):
        # For DMs, get messages between current user and another user
        # Room format: dm_username1_username2
        try:
            usernames = room.split('_')[1:]
            if len(usernames) == 2:
                username1, username2 = usernames[0], usernames[1]
                
                # Ensure current user is one of the participants
                if current_user.username not in [username1, username2]:
                    return jsonify({'success': False, 'message': 'Unauthorized access to this chat'})
                
                # Get the other user's username
                other_username = username1 if current_user.username == username2 else username2
                other_user = User.query.filter_by(username=other_username).first()
                
                if not other_user:
                    return jsonify({'success': False, 'message': 'Other user not found'})
                
                messages = Message.query.filter(
                    ((Message.sender_id == current_user.id) & (Message.recipient_id == other_user.id)) |
                    ((Message.sender_id == other_user.id) & (Message.recipient_id == current_user.id))
                ).order_by(Message.date_sent.asc()).all()
            else:
                return jsonify({'success': False, 'message': 'Invalid room format'})
        except (ValueError, IndexError):
            return jsonify({'success': False, 'message': 'Invalid room format'})
    else:
        # For other rooms (technique, repertoire, etc.)
        messages = Message.query.filter_by(room=room).order_by(Message.date_sent.asc()).limit(50).all()
    
    print(f"DEBUG: Found {len(messages)} messages for room '{room}'")
    
    message_list = []
    for msg in messages:
        sender = User.query.get(msg.sender_id)
        if sender:  # Only add if sender exists
            message_data = {
                'id': msg.id,
                'sender': sender.username,
                'content': msg.content,
                'date_sent': msg.date_sent.strftime('%I:%M %p'),
                'is_own': msg.sender_id == current_user.id
            }
            message_list.append(message_data)
            print(f"DEBUG: Message {msg.id}: '{msg.content}' from {sender.username}")
    
    print(f"DEBUG: Returning {len(message_list)} messages")
    
    return jsonify({'success': True, 'messages': message_list})

@app.route('/global_search')
def global_search():
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify({'success': True, 'pieces': [], 'users': []})
    
    # Search pieces
    pieces = Piece.query.filter(
        db.or_(
            Piece.title.ilike(f'%{query}%'),
            Piece.composer.ilike(f'%{query}%'),
            Piece.genre.ilike(f'%{query}%'),
            Piece.era.ilike(f'%{query}%')
        )
    ).filter_by(is_approved=True).limit(5).all()
    
    piece_list = []
    for piece in pieces:
        piece_list.append({
            'id': piece.id,
            'title': piece.title,
            'composer': piece.composer,
            'genre': piece.genre,
            'era': piece.era,
            'type': 'piece'
        })
    
    # Search users
    users = User.query.filter(User.username.ilike(f'%{query}%')).limit(5).all()
    user_list = []
    for user in users:
        user_list.append({
            'id': user.id,
            'username': user.username,
            'avatar': user.avatar,
            'bio': user.bio,
            'type': 'user'
        })
    
    return jsonify({
        'success': True, 
        'pieces': piece_list, 
        'users': user_list
    })

@app.route('/search_users')
@login_required
def search_users():
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify({'success': True, 'users': []})
    
    users = User.query.filter(User.username.ilike(f'%{query}%')).limit(10).all()
    user_list = [{'username': user.username, 'avatar': user.avatar} for user in users]
    
    return jsonify({'success': True, 'users': user_list})

@app.route('/start_chat/<username>')
@login_required
def start_chat(username):
    # Direct messaging is temporarily disabled
    return jsonify({
        'success': False, 
        'message': 'Direct messaging is temporarily disabled. Please use the group chat rooms (General, Technique Tips, or Repertoire Discussion) instead. This feature will be available in an upcoming update!'
    })

@app.route('/get_user_suggestions')
@login_required
def get_user_suggestions():
    # Direct messaging is temporarily disabled
    return jsonify({
        'success': False, 
        'message': 'Direct messaging is temporarily disabled. Please use the group chat rooms (General, Technique Tips, or Repertoire Discussion) instead. This feature will be available in an upcoming update!',
        'users': []
    })

@app.route('/admin/cleanup', methods=['POST'])
@login_required
def admin_cleanup():
    if not current_user.username == 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    try:
        # Only delete messages that are clearly fake (not in valid rooms)
        # Keep all user accounts and valid messages
        fake_messages = Message.query.filter(
            ~Message.room.in_(['general', 'technique', 'repertoire']),
            ~Message.room.like('dm_%')  # Keep all DM messages
        ).all()
        
        fake_message_count = len(fake_messages)
        for msg in fake_messages:
            db.session.delete(msg)
        
        # Only delete messages from non-existent users (orphaned messages)
        all_user_ids = [user.id for user in User.query.all()]
        orphaned_messages = Message.query.filter(
            ~Message.sender_id.in_(all_user_ids)
        ).all()
        
        orphaned_count = len(orphaned_messages)
        for msg in orphaned_messages:
            db.session.delete(msg)
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Cleaned up {fake_message_count} fake messages and {orphaned_count} orphaned messages. All user accounts preserved.'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error during cleanup: {str(e)}'})

@app.route('/seed_chat_messages')
@login_required
def seed_chat_messages():
    if current_user.username != 'admin':
        return jsonify({'success': False, 'message': 'Admin only'})
    
    # Clear existing messages
    Message.query.delete()
    
    # No more placeholder messages - start with clean chat
    db.session.commit()
    return jsonify({'success': True, 'message': 'Chat messages cleared and ready for real conversations'})

@app.route('/admin/clear_messages', methods=['POST'])
@login_required
def admin_clear_messages():
    if not current_user.username == 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    try:
        # Clear all messages
        Message.query.delete()
        db.session.commit()
        return jsonify({'success': True, 'message': 'All messages cleared'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error clearing messages: {str(e)}'})

@app.route('/admin/purge_all_fake_data', methods=['POST'])
@login_required
def admin_purge_all_fake_data():
    if not current_user.username == 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    try:
        # Clear ALL messages (including general chat, DMs, etc.)
        Message.query.delete()
        
        # Clear all ratings
        Rating.query.delete()
        
        # Clear all favorites
        Favorite.query.delete()
        
        # Clear all comments
        Comment.query.delete()
        
        # Reset piece ratings to 0
        pieces = Piece.query.all()
        for piece in pieces:
            piece.total_ratings = 0
            piece.difficulty_avg = 0.0
        
        # Keep only the admin user and remove all other users
        users_to_delete = User.query.filter(User.username != 'admin').all()
        for user in users_to_delete:
            db.session.delete(user)
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Purged all fake data: {len(users_to_delete)} users removed, all messages/ratings/comments cleared, pieces reset to 0 ratings'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error during purge: {str(e)}'})





@app.route('/get_online_users')
@login_required
def get_online_users():
    # Get all users (in a real app, you'd track actual online status)
    users = User.query.all()
    user_list = []
    
    for user in users:
        # For now, mark all users as online
        # In a real app, you'd check actual online status
        user_list.append({
            'id': user.id,
            'username': user.username,
            'status': 'online'
        })
    
    return jsonify({'success': True, 'users': user_list})

@app.route('/get_active_dms')
@login_required
def get_active_dms():
    # Direct messaging is temporarily disabled
    return jsonify({
        'success': True, 
        'dms': [],
        'message': 'Direct messaging is temporarily disabled. Please use the group chat rooms instead.'
    })





if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Create admin user if it doesn't exist
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin = User(
                username='admin', 
                email='admin@myviolinrep.com', 
                bio='Platform Administrator',
                password_hash=generate_password_hash('admin123')
            )
            db.session.add(admin)
            db.session.commit()
            print("Admin user created: username='admin', password='admin123'")
        
        # Sample pieces are commented out - no default pieces will be created
        # if Piece.query.count() == 0:
        #     # Create sample pieces here if needed
        #     pass
        
        app.run(debug=True, port=5002)
