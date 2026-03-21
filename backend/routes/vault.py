from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from db import query
from crypto import encrypt, decrypt

vault_bp = Blueprint('vault', __name__)

def decrypt_entry(e):
    if e and e.get('password'):
        e = dict(e)
        e['password'] = decrypt(e['password'])
    return e

@vault_bp.route('/entries', methods=['GET'])
@jwt_required()
def list_entries():
    uid = get_jwt_identity()
    category = request.args.get('category')
    search = request.args.get('search')
    sql, args = 'SELECT * FROM entries WHERE user_id=%s', [uid]
    if category:
        sql += ' AND category=%s'
        args.append(category)
    if search:
        sql += ' AND (name ILIKE %s OR username ILIKE %s OR url ILIKE %s)'
        like = f'%{search}%'
        args += [like, like, like]
    sql += ' ORDER BY updated_at DESC'
    rows = query(sql, tuple(args)) or []
    return jsonify(entries=[decrypt_entry(dict(r)) for r in rows]), 200

@vault_bp.route('/entries', methods=['POST'])
@jwt_required()
def create_entry():
    uid = get_jwt_identity()
    d = request.get_json(silent=True) or {}
    name  = (d.get('name')     or '').strip()
    uname = (d.get('username') or '').strip()
    pw    = (d.get('password') or '').strip()
    if not name or not uname or not pw:
        return jsonify(error='Name, username and password are required.'), 400
    row = query(
        'INSERT INTO entries (user_id,name,url,username,password,category,notes,favourite) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id',
        (uid, name, d.get('url', ''), uname, encrypt(pw),
         d.get('category', 'General'), d.get('notes', ''),
         bool(d.get('favourite', False))), commit=True
    )
    eid = row['id']
    return jsonify(entry=decrypt_entry(dict(query('SELECT * FROM entries WHERE id=%s', (eid,), one=True)))), 201

@vault_bp.route('/entries/<int:eid>', methods=['PUT'])
@jwt_required()
def update_entry(eid):
    uid = get_jwt_identity()
    if not query('SELECT id FROM entries WHERE id=%s AND user_id=%s', (eid, uid), one=True):
        return jsonify(error='Entry not found.'), 404
    d = request.get_json(silent=True) or {}
    query(
        'UPDATE entries SET name=%s,url=%s,username=%s,password=%s,category=%s,notes=%s,favourite=%s WHERE id=%s AND user_id=%s',
        (d.get('name'), d.get('url', ''), d.get('username'), encrypt(d.get('password', '')),
         d.get('category', 'General'), d.get('notes', ''),
         bool(d.get('favourite', False)), eid, uid), commit=True
    )
    return jsonify(entry=decrypt_entry(dict(query('SELECT * FROM entries WHERE id=%s', (eid,), one=True)))), 200

@vault_bp.route('/entries/<int:eid>', methods=['DELETE'])
@jwt_required()
def delete_entry(eid):
    uid = get_jwt_identity()
    if not query('SELECT id FROM entries WHERE id=%s AND user_id=%s', (eid, uid), one=True):
        return jsonify(error='Entry not found.'), 404
    query('DELETE FROM entries WHERE id=%s AND user_id=%s', (eid, uid), commit=True)
    return jsonify(message='Deleted.'), 200