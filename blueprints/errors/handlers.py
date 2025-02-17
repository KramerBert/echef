from flask import render_template, current_app
from . import bp

@bp.app_errorhandler(404)
def not_found_error(error):
    current_app.logger.error(f'Page not found: {error}')
    return render_template('errors/404.html', error=error), 404

@bp.app_errorhandler(500)
def internal_error(error):
    current_app.logger.error(f'Server Error: {error}')
    return render_template('errors/500.html', error=error), 500

@bp.route('/maintenance')
def maintenance():
    return render_template('errors/maintenance.html'), 503
