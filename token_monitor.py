import os
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify
from token_refresh import renovar_token
from dotenv import load_dotenv
from bling_clientes import buscar_detalhes_cliente

app = Flask(__name__)
load_dotenv()

LAST_REFRESH_FILE = 'token_status.json'

def load_token_status():
    try:
        if os.path.exists(LAST_REFRESH_FILE):
            with open(LAST_REFRESH_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        app.logger.error(f"Erro ao carregar status do token: {e}")
    
    return {
        'last_refresh': None,
        'next_refresh': None
    }

def save_token_status(status):
    try:
        with open(LAST_REFRESH_FILE, 'w') as f:
            json.dump(status, f)
    except Exception as e:
        app.logger.error(f"Erro ao salvar status do token: {e}")

def get_token_info():
    status = load_token_status()
    access_token = os.getenv('BLING_ACCESS_TOKEN', '')
    last_refresh = status.get('last_refresh')
    next_refresh = status.get('next_refresh')

    # Se não temos informação de refresh, consideramos o token como não inicializado
    if not last_refresh:
        token_status = 'Não inicializado'
    else:
        last_refresh_dt = datetime.fromisoformat(last_refresh)
        next_refresh_dt = datetime.fromisoformat(next_refresh)
        now = datetime.now()

        if now > next_refresh_dt:
            token_status = 'Expirado'
        else:
            token_status = 'Válido'

    return {
        'access_token': f"{access_token[:10]}..." if access_token else 'Não disponível',
        'last_refresh': last_refresh or 'Nunca',
        'next_refresh': next_refresh or 'Não definido',
        'status': token_status
    }

@app.route('/')
def index():
    return render_template('token_status.html', **get_token_info())

@app.route('/refresh-token', methods=['POST'])
def refresh_token():
    try:
        new_token = renovar_token()
        if new_token:
            now = datetime.now()
            # Assumimos que o token expira em 8 horas
            next_refresh = now + timedelta(hours=7)  # Renovamos 1 hora antes da expiração
            
            status = {
                'last_refresh': now.isoformat(),
                'next_refresh': next_refresh.isoformat()
            }
            save_token_status(status)
            
            return jsonify({
                'success': True,
                **get_token_info()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Falha ao renovar o token'
            })
    except Exception as e:
        app.logger.error(f"Erro ao renovar token: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

# ------------------ NOVA FUNCIONALIDADE: Consulta de Contato por ID ------------------
@app.route('/contato')
def contato_page():
    """Página simples com input para consultar um contato por ID."""
    return render_template('contato_busca.html')

@app.route('/api/contatos/<int:id_cliente>')
def api_buscar_contato(id_cliente: int):
    """Endpoint que consulta a API do Bling e retorna o contato em JSON."""
    try:
        data = buscar_detalhes_cliente(id_cliente)
        if data:
            return jsonify({'success': True, 'data': data})
        return jsonify({'success': False, 'error': 'Contato não encontrado'}), 404
    except Exception as e:
        app.logger.error(f"Erro ao buscar contato {id_cliente}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
# -------------------------------------------------------------------------------------

if __name__ == '__main__':
    app.run(debug=True, port=5000)