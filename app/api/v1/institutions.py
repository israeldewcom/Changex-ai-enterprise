from flask import Blueprint, request, jsonify, g
from app import db
from app.models import Institution, UserRole, Role
from app.auth import jwt_required, admin_required
from app.utils.validators import InstitutionCreateSchema
from marshmallow import ValidationError
from app.utils.pagination import paginate
from app.services.analytics import institution_stats
from app.extensions import cache

bp = Blueprint('institutions', __name__)

@bp.route('', methods=['POST'])
@jwt_required
def create_institution():
    schema = InstitutionCreateSchema()
    try:
        data = schema.load(request.json)
    except ValidationError as e:
        return jsonify({'errors': e.messages}), 400

    inst = Institution(
        name=data['name'],
        type=data['type'],
        domain=data.get('domain'),
        branding=data.get('branding', {}),
        subscription_tier=data.get('subscription_tier', 'free')
    )
    db.session.add(inst)
    db.session.flush()

    # Assign creator as admin
    admin_role = Role.query.filter_by(name='admin').first()
    if not admin_role:
        admin_role = Role(name='admin', permissions=['*'])
        db.session.add(admin_role)
        db.session.flush()

    user_role = UserRole(
        user_id=g.current_user.id,
        institution_id=inst.id,
        role_id=admin_role.id
    )
    db.session.add(user_role)
    db.session.commit()
    return jsonify(inst.to_dict()), 201

@bp.route('/<int:id>', methods=['GET'])
@jwt_required
@cache.cached(timeout=60, query_string=True)
def get_institution(id):
    inst = db.session.get(Institution, id)
    if not inst:
        return jsonify({'msg': 'Institution not found'}), 404
    return jsonify(inst.to_dict())

@bp.route('/<int:id>/stats', methods=['GET'])
@jwt_required
@admin_required(institution_id_param='id')
def stats(id):
    stats = institution_stats(id)
    return jsonify(stats)

@bp.route('/<int:id>/users', methods=['GET'])
@jwt_required
@admin_required(institution_id_param='id')
def list_users(id):
    from app.api.v1.users import user_schema
    query = UserRole.query.filter_by(institution_id=id).join(User).with_entities(User)
    return paginate(query, user_schema, 'api.users', institution_id=id)

@bp.route('/<int:id>/settings', methods=['PATCH'])
@jwt_required
@admin_required(institution_id_param='id')
def update_settings(id):
    inst = db.session.get(Institution, id)
    data = request.get_json()
    if 'settings' in data:
        inst.settings.update(data['settings'])
    if 'branding' in data:
        inst.branding.update(data['branding'])
    db.session.commit()
    return jsonify(inst.to_dict())
