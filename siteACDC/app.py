from flask import Flask, render_template, request, redirect, session, url_for
from flask_mysqldb import MySQL
import bcrypt
import config

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

app.config['MYSQL_HOST'] = config.MYSQL_HOST
app.config['MYSQL_USER'] = config.MYSQL_USER
app.config['MYSQL_PASSWORD'] = config.MYSQL_PASSWORD
app.config['MYSQL_DB'] = config.MYSQL_DB

mysql = MySQL(app)

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
    cur.execute("SELECT codigo, nome, saldovirtualtotal FROM produto")
    produtos = cur.fetchall()
    cur.close()
    return render_template('dashboard.html', produtos=produtos, usuario=session['usuario'])

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
    app.run(debug=True)