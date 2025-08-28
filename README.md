# 🎻 MyViolinRep - Violin Repertoire Difficulty & Community Hub

A beautifully designed, interactive platform where violinists can discover, rank, and discuss repertoire. Blending the sophistication of a curated classical archive with the vibrancy of a social platform, MyViolinRep becomes the ultimate space to explore violin music, share experiences, and connect with other players.

## ✨ Features

### 🏠 Homepage
- **Elegant Hero Banner** with gradient background (deep burgundy → gold)
- **Quick Access Cards**: Browse All Pieces, Join the Discussion, Leaderboard
- **Highlights Section**: Featured piece of the week, recently approved additions, top performers
- **Animated Violin Visual** with floating music notes

### 📚 Repertoire Library
- **Advanced Search & Filters**: By composer, difficulty, era, genre, technical elements
- **Beautiful Piece Cards** with hover animations and difficulty meters
- **Technical Tags**: spiccato, double stops, harmonics, shifting, left-hand pizzicato
- **Difficulty Rating System**: 1-10 scale with violin scroll difficulty meter
- **Pagination** and sorting options

### 💬 Community Features
- **Piece-Specific Forums** for each repertoire piece
- **User Profiles** with contribution scores and badges
- **Leaderboard System** with monthly rankings
- **Direct Messaging** and community chat
- **Activity Feed** showing community engagement

### 🎯 User Interaction
- **Difficulty Rating System** with real-time updates
- **Comment System** with upvoting and tagging
- **User Badges**: Bronze/Silver/Gold ranks for milestones
- **Contribution Tracking** for repertoire submissions

### 📝 Content Management
- **User Submission Form** for new pieces
- **Admin Approval Workflow** for quality control
- **Metadata Management**: composer, era, genre, opus, length
- **Performance Links** and recording integration

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd MyViolinRep
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Open your browser**
   Navigate to `http://localhost:5000`

### Default Admin Account
- **Username**: `admin`
- **Password**: `admin123`

## 🎨 Design Features

### Visual Theme
- **Gradients**: Classy burgundy → champagne gold, deep navy → silver
- **Typography**: Playfair Display (titles) + Inter (body text)
- **Icons**: Minimalist line art with violin flourishes
- **Layout**: Clean grid, elegant white space, soft shadows

### Animations & UX
- **Hover Effects**: Cards tilt slightly, smooth transitions
- **Scroll Animations**: AOS (Animate On Scroll) library integration
- **Floating Music Notes**: Continuous background animation
- **Violin Animation**: Hero section with animated violin and bow
- **Progress Bars**: Reading progress and difficulty meters
- **Ripple Effects**: Button click animations

## 🏗️ Architecture

### Backend (Flask)
- **Flask-SQLAlchemy**: Database ORM
- **Flask-Login**: User authentication
- **SQLite Database**: Lightweight, file-based storage
- **RESTful API**: JSON endpoints for AJAX interactions

### Frontend
- **HTML5**: Semantic markup
- **CSS3**: Custom properties, Grid/Flexbox, animations
- **JavaScript**: ES6+, modular architecture
- **Responsive Design**: Mobile-first approach

### Database Models
- **User**: Authentication, profiles, scores
- **Piece**: Repertoire metadata, difficulty ratings
- **Rating**: User difficulty assessments
- **Comment**: Forum discussions and tips
- **Message**: Direct messaging system

## 🔧 Configuration

### Environment Variables
Create a `.env` file in the root directory:
```env
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///violinrep.db
DEBUG=True
```

### Database
The application automatically creates the database and sample data on first run. Sample pieces include:
- Tchaikovsky Violin Concerto in D Major
- Bach Violin Sonata No. 1
- Paganini Caprice No. 24

## 📱 Responsive Design

- **Mobile-First**: Optimized for all screen sizes
- **Touch-Friendly**: Large touch targets and gestures
- **Progressive Enhancement**: Core functionality works without JavaScript
- **Accessibility**: ARIA labels, keyboard navigation, focus indicators

## 🚀 Deployment

### Local Development
```bash
python app.py
```

### Production Deployment
1. Set `DEBUG=False` in environment
2. Use production WSGI server (Gunicorn, uWSGI)
3. Configure reverse proxy (Nginx, Apache)
4. Set up SSL certificates
5. Configure database for production use

## 🧪 Testing

### Manual Testing
- User registration and login
- Piece submission and approval
- Difficulty rating system
- Forum commenting
- Search and filtering

### Browser Compatibility
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## 🔮 Future Enhancements

- **Practice Tracker**: Calendar + streaks
- **Teacher/Student Mode**: Assignments and progress tracking
- **Mobile App**: Native iOS/Android applications
- **Collaboration Hub**: Chamber group repertoire planning
- **Sheet Music Integration**: PDF uploads and viewing
- **Audio Analysis**: AI-powered difficulty assessment
- **Social Features**: Following, notifications, events

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Font Awesome** for beautiful icons
- **Google Fonts** for typography
- **AOS Library** for scroll animations
- **Flask Community** for the excellent web framework

## 📞 Support

For questions, issues, or feature requests:
- Create an issue on GitHub
- Contact the development team
- Check the documentation

---

**MyViolinRep** - Where violinists connect, discover, and grow together. 🎻✨
