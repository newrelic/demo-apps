"""
Main routes - Home page and mode switching.
"""

from flask import Blueprint, redirect, url_for

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    """Home page - redirects to repair mode."""
    return redirect(url_for('repair.repair_mode'))
