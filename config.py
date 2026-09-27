# config.py
import os
import secrets
import warnings
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


def _get_secret_key():
    key = os.environ.get('SECRET_KEY')
    if key:
        return key
    warnings.warn(
        'SECRET_KEY não definida no ambiente. Usando uma chave aleatória gerada '
        'a cada início do servidor (isso invalida sessões/cookies a cada reinício). '
        'Defina a variável de ambiente SECRET_KEY antes de rodar em produção.',
        RuntimeWarning
    )
    return secrets.token_hex(32)


class Config:
    SECRET_KEY = _get_secret_key()
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'sqlite:///' + os.path.join(basedir, 'app.db')  # ESTA LINHA É CRÍTICA
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)


class DevelopmentConfig(Config):
    DEBUG = True  # Ativa o modo debug em desenvolvimento
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
                              'sqlite:///' + os.path.join(basedir, 'app_dev.db')  # Banco de dados separado para dev


class TestingConfig(Config):
    TESTING = True  # Ativa o modo de teste
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
                              'sqlite:///:memory:'  # Banco de dados em memória para testes


class ProductionConfig(Config):
    DEBUG = False  # Desativa o modo debug em produção
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')  # Em produção, DATABASE_URL deve ser definida
    # Outras configurações de produção, como loggers mais robustos, etc.


# Dicionário para mapear nomes de configuração para classes
config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig  # Configuração padrão
}
