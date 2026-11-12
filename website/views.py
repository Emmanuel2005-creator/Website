from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from . import db
from .models import Note

views = Blueprint('views', __name__)


@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    draft = ''
    if request.method == 'POST':
        draft = request.form.get('note', '')
        if not draft.strip():
            flash('Write something before saving your note.', 'error')
        elif len(draft) > 10000:
            flash('Keep your note within 10,000 characters.', 'error')
        else:
            db.session.add(Note(data=draft, user_id=current_user.id))
            db.session.commit()
            flash('Note saved. One less thing on your mind.', 'success')
            return redirect(url_for('views.home'))
    notes = Note.query.filter_by(user_id=current_user.id).order_by(Note.date.desc(), Note.id.desc()).all()
    return render_template('home.html', notes=notes, draft=draft)


@views.route('/delete-note', methods=['POST'])
@login_required
def delete_note():
    payload = request.get_json(silent=True)
    note_id = payload.get('noteId') if isinstance(payload, dict) else None
    if type(note_id) is not int or not 0 < note_id <= 9223372036854775807:
        return jsonify(error='Provide a valid note ID.'), 400
    note = Note.query.filter_by(id=note_id, user_id=current_user.id).first()
    if note is None:
        return jsonify(error='This note could not be found.'), 404
    db.session.delete(note)
    db.session.commit()
    flash('Note deleted. A little more space.', 'success')
    return jsonify({})


@views.route('/health')
def health():
    # Liveness only: no database or account details.
    return jsonify(status='ok')
