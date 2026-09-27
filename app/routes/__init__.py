from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user, login_required

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.type == 'warehouse':
            return redirect(url_for('trips.dashboard'))
        else:  # manager
            return redirect(url_for('reports.dashboard'))
    return render_template('index.html', title='Início')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.type == 'warehouse':
        return redirect(url_for('trips.dashboard'))
    else:  # manager
        return redirect(url_for('reports.dashboard'))
