"""MCP (Model Context Protocol) compatible endpoint for Flask API."""

import os
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

mcp_bp = Blueprint('mcp', __name__)


def verify_api_key(request) -> bool:
    """Verify the MCP API key from request headers.
    
    Args:
        request: Flask request object
        
    Returns:
        True if API key is valid, False otherwise
    """
    api_key = request.headers.get('x-api-key')
    expected_key = os.getenv('MCP_API_KEY')
    
    if not expected_key:
        logger.warning("MCP_API_KEY environment variable not set")
        return False
    
    if not api_key:
        logger.warning("Missing x-api-key header in MCP request")
        return False
    
    is_valid = api_key == expected_key
    if not is_valid:
        logger.warning("Invalid MCP API key provided")
    
    return is_valid


def handle_list_pages(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle list_pages MCP method.
    
    Args:
        params: Method parameters
        
    Returns:
        Mock page list response
    """
    mock_pages = [
        {
            "id": "page_001",
            "title": "Getting Started Guide",
            "content": "Welcome to our API documentation...",
            "created_at": "2025-01-15T10:30:00Z",
            "updated_at": "2025-01-20T14:45:00Z",
            "author": "API Team",
            "status": "published"
        },
        {
            "id": "page_002", 
            "title": "Authentication Methods",
            "content": "Learn how to authenticate with our API...",
            "created_at": "2025-01-16T09:15:00Z",
            "updated_at": "2025-01-22T11:30:00Z",
            "author": "Security Team",
            "status": "published"
        },
        {
            "id": "page_003",
            "title": "Rate Limiting",
            "content": "Understanding API rate limits and best practices...",
            "created_at": "2025-01-18T16:20:00Z",
            "updated_at": "2025-01-21T13:10:00Z",
            "author": "Infrastructure Team",
            "status": "draft"
        }
    ]
    
    # Apply filters if provided in params
    status_filter = params.get('status')
    if status_filter:
        mock_pages = [page for page in mock_pages if page['status'] == status_filter]
    
    limit = params.get('limit', len(mock_pages))
    mock_pages = mock_pages[:limit]
    
    return {
        "pages": mock_pages,
        "total": len(mock_pages),
        "page": params.get('page', 1),
        "per_page": limit
    }


def handle_create_page(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle create_page MCP method.
    
    Args:
        params: Method parameters containing page data
        
    Returns:
        Mock created page response
    """
    # Generate mock ID and timestamps
    page_id = f"page_{uuid.uuid4().hex[:8]}"
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    # Extract page data from params
    title = params.get('title', 'Untitled Page')
    content = params.get('content', '')
    author = params.get('author', 'Anonymous')
    status = params.get('status', 'draft')
    
    created_page = {
        "id": page_id,
        "title": title,
        "content": content,
        "created_at": timestamp,
        "updated_at": timestamp,
        "author": author,
        "status": status,
        "word_count": len(content.split()) if content else 0,
        "revision": 1
    }
    
    logger.info(f"Mock created page: {page_id} - {title}")
    
    return {
        "page": created_page,
        "message": f"Page '{title}' created successfully"
    }


def handle_update_page(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle update_page MCP method.
    
    Args:
        params: Method parameters containing page ID and update data
        
    Returns:
        Mock updated page response
    """
    page_id = params.get('id')
    if not page_id:
        raise ValueError("Page ID is required for update_page method")
    
    # Mock existing page data
    existing_page = {
        "id": page_id,
        "title": "Existing Page Title",
        "content": "Existing page content...",
        "created_at": "2025-01-15T10:30:00Z",
        "updated_at": "2025-01-20T14:45:00Z",
        "author": "Original Author",
        "status": "published",
        "revision": 3
    }
    
    # Apply updates
    updated_page = existing_page.copy()
    updated_page.update({
        "title": params.get('title', existing_page['title']),
        "content": params.get('content', existing_page['content']),
        "status": params.get('status', existing_page['status']),
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "revision": existing_page['revision'] + 1
    })
    
    # Update word count if content changed
    if 'content' in params:
        updated_page['word_count'] = len(updated_page['content'].split())
    
    logger.info(f"Mock updated page: {page_id}")
    
    return {
        "page": updated_page,
        "message": f"Page '{updated_page['title']}' updated successfully",
        "changes": list(params.keys())
    }


@mcp_bp.route('/mcp', methods=['POST'])
def mcp_endpoint():
    """MCP-compatible POST endpoint for handling various MCP methods.
    
    Expected JSON body:
    {
        "method": "list_pages|create_page|update_page",
        "params": {}
    }
    
    Returns:
        JSON response with success/error status and data
    """
    # Verify API key authentication
    if not verify_api_key(request):
        return jsonify({
            "success": False,
            "error": "Unauthorized"
        }), 401
    
    # Parse JSON request body
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "Invalid JSON or empty request body"
            }), 400
    except Exception as e:
        logger.error(f"Failed to parse JSON request: {e}")
        return jsonify({
            "success": False,
            "error": "Invalid JSON format"
        }), 400
    
    # Validate required fields
    method = data.get('method')
    if not method:
        return jsonify({
            "success": False,
            "error": "Missing required field: method"
        }), 400
    
    params = data.get('params', {})
    if not isinstance(params, dict):
        return jsonify({
            "success": False,
            "error": "Field 'params' must be an object/dictionary"
        }), 400
    
    # Handle MCP methods
    try:
        if method == 'list_pages':
            result_data = handle_list_pages(params)
        elif method == 'create_page':
            result_data = handle_create_page(params)
        elif method == 'update_page':
            result_data = handle_update_page(params)
        else:
            return jsonify({
                "success": False,
                "error": "Unknown MCP method"
            }), 400
        
        # Return successful response
        return jsonify({
            "success": True,
            "data": result_data,
            "method": method,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 200
        
    except ValueError as e:
        logger.warning(f"MCP method validation error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400
    except Exception as e:
        logger.error(f"MCP method execution error: {e}")
        return jsonify({
            "success": False,
            "error": "Internal server error processing MCP method"
        }), 500


# Register blueprint variable for import
bp = mcp_bp

# Example MCP Request:
# POST /mcp
# Headers:
#   x-api-key: MY_SECRET
# Body:
# {
#   "method": "list_pages",
#   "params": {}
# }
#
# Example responses:
#
# Success (list_pages):
# {
#   "success": true,
#   "data": {
#     "pages": [...],
#     "total": 3,
#     "page": 1,
#     "per_page": 10
#   },
#   "method": "list_pages",
#   "timestamp": "2025-10-22T15:30:00Z"
# }
#
# Success (create_page):
# {
#   "success": true,
#   "data": {
#     "page": {
#       "id": "page_abc123",
#       "title": "New Page",
#       "content": "Page content...",
#       "created_at": "2025-10-22T15:30:00Z",
#       "status": "draft"
#     },
#     "message": "Page 'New Page' created successfully"
#   },
#   "method": "create_page",
#   "timestamp": "2025-10-22T15:30:00Z"
# }
#
# Error (unauthorized):
# {
#   "success": false,
#   "error": "Unauthorized"
# }
#
# Error (unknown method):
# {
#   "success": false,
#   "error": "Unknown MCP method"
# }