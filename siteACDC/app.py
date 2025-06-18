from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from flask_mysqldb import MySQL
import bcrypt
import config
from datetime import datetime

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

app.config['MYSQL_HOST'] = config.MYSQL_HOST
app.config['MYSQL_USER'] = config.MYSQL_USER
app.config['MYSQL_PASSWORD'] = config.MYSQL_PASSWORD
app.config['MYSQL_DB'] = config.MYSQL_DB

mysql = MySQL(app)

def criar_tabelas():
    """Criar tabelas necessárias se não existirem"""
    cur = mysql.connection.cursor()
    
    # Tabela de pedidos
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cabpedidos (
            idpedido INT AUTO_INCREMENT PRIMARY KEY,
            idparceiro INT DEFAULT 1,
            dtpedido DATETIME DEFAULT CURRENT_TIMESTAMP,
            codusu INT NOT NULL,
            total DECIMAL(10,2) DEFAULT 0.00,
            status VARCHAR(50) DEFAULT 'PENDENTE',
            FOREIGN KEY (codusu) REFERENCES usuarios(codusu)
        )
    """)
    
    # Tabela de itens do pedido
    cur.execute("""
        CREATE TABLE IF NOT EXISTS itepedidos (
            iditens INT AUTO_INCREMENT PRIMARY KEY,
            idpedido INT NOT NULL,
            codprod INT NOT NULL,
            quantidade INT NOT NULL,
            vlrunit DECIMAL(10,2) NOT NULL,
            vlrtot DECIMAL(10,2) NOT NULL,
            FOREIGN KEY (idpedido) REFERENCES cabpedidos(idpedido),
            FOREIGN KEY (codprod) REFERENCES produto(codigo)
        )
    """)
    
    mysql.connection.commit()
    cur.close()

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha'].encode('utf-8')

        cur = mysql.connection.cursor()
        cur.execute("SELECT codusu, nomeusu, senha FROM usuarios WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()

        if user and bcrypt.checkpw(senha, user[2].encode('utf-8')):
            session['usuario'] = {'codusu': user[0], 'nomeusu': user[1]}
            return redirect(url_for('dashboard'))
        else:
            msg = 'Login inválido!'
    return render_template('login.html', msg=msg)

@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    # Buscar produtos com preço
    cur.execute("SELECT codigo, nome, saldovirtualtotal, preco FROM produto WHERE saldovirtualtotal >= 0 ORDER BY nome")
    produtos = cur.fetchall()
    cur.close()
    return render_template('dashboard.html', produtos=produtos, usuario=session['usuario'])

@app.route('/finalizar_pedido', methods=['POST'])
def finalizar_pedido():
    if 'usuario' not in session:
        return jsonify({'success': False, 'message': 'Usuário não logado'})
    
    try:
        data = request.get_json()
        itens = data.get('itens', [])
        
        if not itens:
            return jsonify({'success': False, 'message': 'Carrinho vazio'})
        
        cur = mysql.connection.cursor()
        
        # Verificar estoque disponível
        for item in itens:
            cur.execute("SELECT saldovirtualtotal FROM produto WHERE codigo = %s", (item['codigo'],))
            produto = cur.fetchone()
            
            if not produto:
                return jsonify({'success': False, 'message': f'Produto {item["codigo"]} não encontrado'})
            
            if produto[0] < item['quantidade']:
                return jsonify({'success': False, 'message': f'Estoque insuficiente para {item["nome"]}'})
        
        # Calcular total do pedido
        total_pedido = sum(item['preco'] * item['quantidade'] for item in itens)
        
        # Inserir cabeçalho do pedido
        cur.execute("""
            INSERT INTO cabpedidos (idparceiro, dtpedido, codusu)
            VALUES (%s, %s, %s)
        """, (1, datetime.now(), session['usuario']['codusu']))


        pedido_id = cur.lastrowid
        
        # Inserir itens do pedido e atualizar estoque
        for item in itens:
            vlr_total_item = item['preco'] * item['quantidade']
            
            # Inserir item do pedido
            cur.execute("""
                INSERT INTO itepedidos (idpedido, codprod, quantidade, vlrunit, vlrtot)
                VALUES (%s, %s, %s, %s, %s)
            """, (pedido_id, item['codigo'], item['quantidade'], item['preco'], vlr_total_item))
            
            # Atualizar estoque
            cur.execute("""
                UPDATE produto 
                SET saldovirtualtotal = saldovirtualtotal - %s 
                WHERE codigo = %s
            """, (item['quantidade'], item['codigo']))
        
        mysql.connection.commit()
        cur.close()
        
        return jsonify({
            'success': True, 
            'message': 'Pedido realizado com sucesso',
            'pedido_id': pedido_id
        })
        
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'success': False, 'message': f'Erro interno: {str(e)}'})

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST':
        nomeusu = request.form['nomeusu']
        documento = request.form['documento']
        email = request.form['email']
        senha = request.form['senha'].encode('utf-8')
        senha_hash = bcrypt.hashpw(senha, bcrypt.gensalt()).decode('utf-8')

        cur = mysql.connection.cursor()
        try:
            cur.execute("INSERT INTO usuarios (nomeusu, documento, email, senha) VALUES (%s, %s, %s, %s)",
                        (nomeusu, documento, email, senha_hash))
            mysql.connection.commit()
            msg = 'Usuário cadastrado com sucesso!'
            return redirect(url_for('login'))
        except Exception as e:
            msg = 'Erro ao cadastrar: ' + str(e)
        finally:
            cur.close()
    return render_template('register.html', msg=msg)

if __name__ == '__main__':
    with app.app_context():
        criar_tabelas()
    app.run(debug=True)