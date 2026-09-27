# run.py
import os
from app import create_app, db
from app.models import User, Vehicle, Department, Driver, Trip, Schedule
from datetime import datetime

# Criar a instância da aplicação
app = create_app()

@app.shell_context_processor
def make_shell_context():
    """
    Adiciona objetos ao contexto do shell Flask para facilitar testes e desenvolvimento.
    Permite acessar modelos e objetos diretamente no shell sem precisar importá-los.
    """
    return {
        'db': db,
        'User': User,
        'Vehicle': Vehicle,
        'Department': Department,
        'Driver': Driver,
        'Trip': Trip,
        'Schedule': Schedule,
        'datetime': datetime
    }

if __name__ == '__main__':
    """
    Executa a aplicação quando o script é executado diretamente.
    Em produção, é recomendado usar um servidor WSGI como Gunicorn.
    """
    app.run(debug=True)
