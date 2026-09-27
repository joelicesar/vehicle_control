# app/__init__.py
from flask import Flask, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime, timedelta # Importar timedelta para PERMANENT_SESSION_LIFETIME

# Instâncias de extensões
db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login' # Define a rota de login para redirecionamento automático
login.login_message = 'Por favor, faça login para acessar esta página.' # Mensagem de login


def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config') # Agora é 'app.config.Config'

    # Inicializar extensões com o aplicativo Flask
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)

    # Importar e registrar Blueprints
    from app.routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.routes.main import bp as main_bp
    app.register_blueprint(main_bp) # Não precisa de url_prefix se for a raiz

    from app.routes.trips import bp as trips_bp
    app.register_blueprint(trips_bp, url_prefix='/trips')

    from app.routes.reports import bp as reports_bp
    app.register_blueprint(reports_bp, url_prefix='/reports')

    from app.routes.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    from app.routes.schedules import bp as schedules_bp
    app.register_blueprint(schedules_bp, url_prefix='/schedules')

    # Registrar manipuladores de erro personalizados
    # CORREÇÃO: Usando importação relativa para o módulo de erros dentro do pacote 'app'
    # Certifique-se de que app/templates/__init__.py e app/templates/errors/__init__.py existem (mesmo que vazios)
    from .templates.errors.errors import page_not_found, internal_server_error
    app.register_error_handler(404, page_not_found)
    app.register_error_handler(500, internal_server_error)

    # Configuração de Logging
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/vehicle_control.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('Vehicle Control Startup')

    # --- Filtros de Template e Processadores de Contexto (Movidos de run.py) ---

    @app.template_filter('date')
    def date_filter(value, format='%d/%m/%Y'):
        """
        Filtro para formatar datas em templates.
        Uso: {{ data|date }} ou {{ data|date('%Y-%m-%d') }}
        """
        if value is None:
            return ""
        return value.strftime(format)

    @app.template_filter('datetimeformat') # Mantendo o nome original para compatibilidade
    @app.template_filter('datetime') # Adicionando o nome 'datetime' também
    def datetime_filter(value, format='%d/%m/%Y %H:%M'):
        """
        Filtro para formatar data e hora em templates.
        Uso: {{ data|datetime }} ou {{ data|datetime('%H:%M') }}
        """
        if value is None:
            return ""
        if isinstance(value, datetime): # Garantir que é um objeto datetime
            return value.strftime(format)
        return value # Retorna o valor original se não for um objeto datetime

    @app.template_filter('currency')
    def currency_filter(value):
        """
        Filtro para formatar valores monetários em templates.
        Uso: {{ valor|currency }}
        """
        if value is None:
            return "R$ 0,00"
        # Formatação para moeda brasileira (separador de milhar '.', separador decimal ',')
        return f"R$ {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

    @app.context_processor
    def utility_processor():
        """
        Adiciona funções úteis ao contexto de todos os templates.
        """
        def format_distance(km):
            """Formata distância em km"""
            if km is None:
                return "0 km"
            # Formatação para distância (separador de milhar '.', separador decimal ',')
            return f"{km:,.1f} km".replace(',', 'X').replace('.', ',').replace('X', '.')

        def format_time_ago(dt):
            """Formata tempo decorrido desde uma data"""
            if dt is None:
                return ""
            now = datetime.now()
            diff = now - dt
            days = diff.days
            hours, remainder = divmod(diff.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            if days > 0:
                return f"{days} {'dia' if days == 1 else 'dias'} atrás"
            elif hours > 0:
                return f"{hours} {'hora' if hours == 1 else 'horas'} atrás"
            elif minutes > 0:
                return f"{minutes} {'minuto' if minutes == 1 else 'minutos'} atrás"
            else:
                return "agora mesmo"
        return dict(
            format_distance=format_distance,
            format_time_ago=format_time_ago,
            now=datetime.now()
        )
    # --- Fim dos Filtros de Template e Processadores de Contexto ---

    return app

# Importar modelos para que o Flask-Migrate os detecte
from app import models
