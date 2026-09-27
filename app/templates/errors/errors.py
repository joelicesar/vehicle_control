# app/templates/errors/errors.py
from flask import render_template


def page_not_found(e):
    """
    Manipulador de erro para 404 Not Found.
    """
    return render_template('errors/404.html'), 404


def internal_server_error(e):
    """
    Manipulador de erro para 500 Internal Server Error.
    """
    return render_template('errors/500.html'), 500
