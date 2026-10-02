from flask import Blueprint, jsonify, request
from src.models.note import Note, db
from src.services.translation import TranslationError, SUPPORTED_LANGUAGES, generate_note_output

note_bp = Blueprint('note', __name__)

@note_bp.route('/notes', methods=['GET'])
def get_notes():
    """Get all notes, ordered by most recently updated"""
    notes = Note.query.order_by(Note.updated_at.desc()).all()
    return jsonify([note.to_dict() for note in notes])

@note_bp.route('/notes', methods=['POST'])
def create_note():
    """Create a new note"""
    try:
        data = request.json
        if not data or 'title' not in data or 'content' not in data:
            return jsonify({'error': 'Title and content are required'}), 400
        
        note = Note(title=data['title'], content=data['content'])
        db.session.add(note)
        db.session.commit()
        return jsonify(note.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@note_bp.route('/notes/<int:note_id>', methods=['GET'])
def get_note(note_id):
    """Get a specific note by ID"""
    note = Note.query.get_or_404(note_id)
    return jsonify(note.to_dict())

@note_bp.route('/notes/<int:note_id>', methods=['PUT'])
def update_note(note_id):
    """Update a specific note"""
    try:
        note = Note.query.get_or_404(note_id)
        data = request.json
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        note.title = data.get('title', note.title)
        note.content = data.get('content', note.content)
        db.session.commit()
        return jsonify(note.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@note_bp.route('/notes/<int:note_id>/translate', methods=['POST'])
def translate_note(note_id):
    """Generate a translated preview for a specific note."""
    return _generate_note_preview(note_id, 'translate')

@note_bp.route('/notes/<int:note_id>/rewrite', methods=['POST'])
def rewrite_note(note_id):
    """Generate a translated and polished preview for a specific note."""
    return _generate_note_preview(note_id, 'rewrite')

def _generate_note_preview(note_id, operation):
    note = Note.query.get_or_404(note_id)
    data = request.get_json(silent=True) or {}
    language = data.get('language', '')

    if language not in SUPPORTED_LANGUAGES:
        return jsonify({
            'error': 'Unsupported target language',
            'supported_languages': SUPPORTED_LANGUAGES,
        }), 400

    try:
        result = generate_note_output(note.title, note.content, language, operation)
        return jsonify({
            'operation': operation,
            'language': language,
            'title': result['title'],
            'content': result['content'],
        })
    except TranslationError as error:
        return jsonify({'error': str(error)}), 502

@note_bp.route('/notes/<int:note_id>', methods=['DELETE'])
def delete_note(note_id):
    """Delete a specific note"""
    try:
        note = Note.query.get_or_404(note_id)
        db.session.delete(note)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@note_bp.route('/notes/search', methods=['GET'])
def search_notes():
    """Search notes by title or content"""
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    
    notes = Note.query.filter(
        (Note.title.contains(query)) | (Note.content.contains(query))
    ).order_by(Note.updated_at.desc()).all()
    
    return jsonify([note.to_dict() for note in notes])

