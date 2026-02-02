from flask import Blueprint, render_template, session, redirect, url_for

agent_bp = Blueprint('agent', __name__, url_prefix='/agent')

@agent_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('user_type') != 'health_agent':
        return redirect(url_for('login.login'))
    return render_template('agent_dashboard.html')
