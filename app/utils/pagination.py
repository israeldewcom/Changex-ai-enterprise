"""
Pagination utilities supporting both offset/limit and cursor-based.
"""
from flask import request, url_for
from typing import Optional, Any, Dict
import base64

def paginate(query, schema, endpoint, cursor_field='id', **kwargs):
    """
    Paginate a SQLAlchemy query. Supports both offset/limit and cursor-based.
    If cursor is provided, use cursor-based pagination.
    """
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    cursor = request.args.get('cursor')
    
    if cursor:
        # Cursor-based pagination
        try:
            cursor_value = base64.urlsafe_b64decode(cursor.encode()).decode()
            # Assuming cursor is the value of cursor_field
            if cursor_field == 'id':
                query = query.filter(getattr(query.entity, cursor_field) > cursor_value)
            else:
                query = query.filter(getattr(query.entity, cursor_field) > cursor_value)
        except Exception:
            pass
    
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    
    items = schema.dump(paginated.items, many=True)
    
    # Generate next cursor if more items
    next_cursor = None
    if paginated.has_next:
        last_item = paginated.items[-1]
        if hasattr(last_item, cursor_field):
            cursor_value = str(getattr(last_item, cursor_field))
            next_cursor = base64.urlsafe_b64encode(cursor_value.encode()).decode()
    
    return {
        'items': items,
        'total': paginated.total,
        'page': page,
        'per_page': per_page,
        'pages': paginated.pages,
        'next': url_for(endpoint, page=page+1, per_page=per_page, **kwargs) if paginated.has_next else None,
        'prev': url_for(endpoint, page=page-1, per_page=per_page, **kwargs) if paginated.has_prev else None,
        'next_cursor': next_cursor
    }
