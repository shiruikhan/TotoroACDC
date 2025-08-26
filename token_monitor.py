"""Aplicação Flask para monitorar e renovar o token do Bling e consultar contatos.

Rotas principais:
- GET /: Dashboard com status do token
- POST /refresh-token: Renova o token e atualiza o status persistido
- GET /api/contatos/<id>: Retorna detalhes do contato por ID (via API Bling)
"""
import os
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, render_template_string
from token_refresh import renovar_token
from dotenv import load_dotenv
from bling_clientes import buscar_detalhes_cliente

app = Flask(__name__, static_url_path='/static', static_folder='static')
load_dotenv()

LAST_REFRESH_FILE = 'token_status.json'


def load_token_status() -> dict:
    """Carrega o status de token do arquivo JSON persistido.

    Retorna um dicionário com as chaves: last_refresh e next_refresh.
    """
    try:
        if os.path.exists(LAST_REFRESH_FILE):
            with open(LAST_REFRESH_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        app.logger.error("Erro ao carregar status do token: %s", e)

    return {
        'last_refresh': None,
        'next_refresh': None
    }


def save_token_status(status: dict) -> None:
    """Salva o status de token no arquivo JSON persistido."""
    try:
        with open(LAST_REFRESH_FILE, 'w') as f:
            json.dump(status, f)
    except Exception as e:
        app.logger.error("Erro ao salvar status do token: %s", e)


def get_token_info() -> dict:
    """Obtém informações atuais do token (mascarado) e janelas de atualização.

    Retorna chaves: access_token (mascarado), last_refresh, next_refresh e status.
    O campo "status" assume valores em minúsculo compatíveis com o template: 
    "válido", "expirado" ou "não inicializado".
    """
    status = load_token_status()
    access_token = os.getenv('BLING_ACCESS_TOKEN', '')
    last_refresh = status.get('last_refresh')
    next_refresh = status.get('next_refresh')

    if not last_refresh:
        token_status = 'não inicializado'
    else:
        last_refresh_dt = datetime.fromisoformat(last_refresh)
        next_refresh_dt = datetime.fromisoformat(next_refresh)
        now = datetime.now()

        if now > next_refresh_dt:
            token_status = 'expirado'
        else:
            token_status = 'válido'

    token_masked = f"{access_token[:10]}..." if access_token else 'Não disponível'

    return {
        'access_token': token_masked,
        'last_refresh': last_refresh or 'Nunca',
        'next_refresh': next_refresh or 'Não definido',
        'status': token_status
    }


@app.route('/')
def index():
    """Renderiza a página de status do token com dados atuais."""
    return render_template('token_status.html', **get_token_info())


@app.route('/refresh-token', methods=['POST'])
def refresh_token():
    """Renova o token via refresh_token e atualiza o status persistido."""
    try:
        new_token = renovar_token()
        if new_token:
            now = datetime.now()
            # Assumimos que o token expira em 8 horas; renovamos 1 hora antes.
            next_refresh = now + timedelta(hours=7)

            status = {
                'last_refresh': now.isoformat(),
                'next_refresh': next_refresh.isoformat()
            }
            save_token_status(status)
            app.logger.info("Token renovado com sucesso; próxima renovação programada para %s", status['next_refresh'])

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
        app.logger.exception("Erro ao renovar token: %s", e)
        return jsonify({
            'success': False,
            'error': str(e)
        })


# Consulta de contato por ID
@app.route('/contato')
def contato_page():
    """Página simples com input para consultar um contato por ID.

    Se o template contato_busca.html não existir, renderiza um fallback simples.
    """
    template_path = os.path.join(app.root_path, 'templates', 'contato_busca.html')
    if os.path.exists(template_path):
        return render_template('contato_busca.html')
    # Fallback básico inline para evitar erro 500 quando o template não existe
    return render_template_string(
        """
        <!DOCTYPE html>
        <html lang=\"pt-BR\">
        <head>
            <meta charset=\"UTF-8\">
            <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
            <title>Consulta de Contato</title>
            <link rel=\"stylesheet\" href=\"/static/css/styles.css\"> 
        </head>
        <body>
            <div class=\"card container\">
                <h1>Consultar Contato por ID</h1>
                <div>
                    <input type=\"number\" id=\"id_cliente\" placeholder=\"ID do contato\" />
                    <button class=\"btn\" onclick=\"buscar()\">Buscar</button>
                </div>
                <p class=\"muted\">Dica: envie um GET para <code>/api/contatos/&lt;id&gt;</code></p>
                <pre id=\"resultado\" class=\"result\"></pre>
            </div>
            <script>
                async function buscar() {
                    const id = document.getElementById('id_cliente').value;
                    if (!id) { alert('Informe um ID'); return; }
                    const res = await fetch(`/api/contatos/${id}`);
                    const data = await res.json();
                    document.getElementById('resultado').textContent = JSON.stringify(data, null, 2);
                }
            </script>
        </body>
        </html>
        """
    )


@app.route('/api/contatos/<int:id_cliente>')
def api_buscar_contato(id_cliente: int):
    """Consulta a API do Bling e retorna o contato em JSON pelo id_cliente."""
    try:
        data = buscar_detalhes_cliente(id_cliente)
        if data:
            return jsonify({'success': True, 'data': data})
        return jsonify({'success': False, 'error': 'Contato não encontrado'}), 404
    except Exception as e:
        app.logger.exception("Erro ao buscar contato %s: %s", id_cliente, e)
        return jsonify({'success': False, 'error': str(e)}), 500
# -------------------------------------------------------------------------------------


if __name__ == '__main__':
    # Permite configurar debug/porta via variáveis de ambiente.
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    port = int(os.getenv('PORT', '5000'))
    app.run(debug=debug, port=port)