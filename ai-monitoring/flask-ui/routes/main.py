"""
Main routes - Home page and mode switching.
"""

from flask import Blueprint, render_template

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    """Home page - New Relic AIM Demo landing page."""
    return render_template('pages/home.html')
