# 🐾 TotoroACDC — Sistema de Integração Bling ERP

![Bling](https://img.shields.io/badge/Bling-ERP-green)
![Python](https://img.shields.io/badge/Python-3.x-blue)
![MySQL](https://img.shields.io/badge/MySQL-Database-orange)
![Flask](https://img.shields.io/badge/Flask-WebApp-red)
![Status](https://img.shields.io/badge/Status-Ativo-success)

**TotoroACDC** é um sistema completo de integração com a **API v3 do Bling ERP**, desenvolvido em Python. O sistema automatiza a sincronização de produtos, clientes e gerencia tokens de autenticação OAuth2, incluindo uma interface web para monitoramento em tempo real.

---

## 📑 Sumário
1. [📂 Estrutura do Projeto](#-estrutura-do-projeto)  
2. [⚙️ Funcionalidades](#️-funcionalidades)  
3. [🔧 Tecnologias e Dependências](#-tecnologias-e-dependências)  
4. [🚀 Instalação e Configuração](#-instalação-e-configuração)  
5. [📋 Configuração do Ambiente](#-configuração-do-ambiente)
6. [💻 Como Usar](#-como-usar)
7. [🌐 Interface Web](#-interface-web)
8. [📊 Estrutura do Banco de Dados](#-estrutura-do-banco-de-dados)
9. [🔍 Logs e Monitoramento](#-logs-e-monitoramento)
10. [🤝 Contribuição](#-contribuição)
11. [📄 Licença](#-licença)

---

## 📂 Estrutura do Projeto

```
TotoroACDC/
├── main.py                    → Script principal de sincronização de produtos
├── sincronizar_clientes.py    → Script de sincronização de clientes
├── bling_api.py              → Cliente da API v3 do Bling (produtos)
├── bling_clientes.py         → Cliente da API v3 do Bling (clientes)
├── db.py                     → Conexão e operações com MySQL
├── detalhes_bling.py         → Processamento de detalhes dos produtos
├── token_refresh.py          → Renovação automática de tokens OAuth2
├── token_monitor.py          → Interface web Flask para monitoramento
├── logger.py                 → Sistema de logging estruturado
├── requirements.txt          → Dependências Python
├── token_status.json         → Status atual dos tokens
├── templates/
│   └── token_status.html     → Interface web de monitoramento
├── .env                      → Variáveis de ambiente (não versionado)
├── .gitignore               → Arquivos ignorados pelo Git
└── README.md                → Este arquivo
```

---

## ⚙️ Funcionalidades

### 🔄 Sincronização de Produtos
- **Busca paginada** de todos os produtos da API v3 do Bling
- **Mapeamento automático** dos campos para o banco MySQL
- **Upsert em lote** para otimização de performance
- **Atualização de detalhes** com controle de idade dos dados
- **Processamento de imagens** e dimensões dos produtos
- **Controle de estoque** em tempo real

### 👥 Sincronização de Clientes
- **Importação completa** de clientes/contatos do Bling
- **Limpeza automática** de campos numéricos (CPF/CNPJ, telefones)
- **Tratamento de endereços** completos
- **Sincronização incremental** com controle de páginas

### 🔐 Gerenciamento de Tokens OAuth2
- **Renovação automática** de access tokens
- **Persistência segura** em arquivo JSON
- **Interface web** para monitoramento em tempo real
- **Refresh manual** via interface web
- **Logs detalhados** de todas as operações

### 🌐 Interface Web de Monitoramento
- **Dashboard em tempo real** do status dos tokens
- **Renovação manual** com feedback visual
- **Histórico de atualizações**
- **Interface responsiva** e intuitiva

---

## 🔧 Tecnologias e Dependências

### Linguagem e Framework
- **Python 3.x** — Linguagem principal
- **Flask 3.x** — Framework web para interface de monitoramento

### Banco de Dados
- **MySQL** — Armazenamento principal dos dados
- **mysql-connector-python 8.4.0** — Driver oficial MySQL

### APIs e Comunicação
- **Requests 2.31+** — Cliente HTTP para API do Bling
- **API v3 do Bling** — Integração com ERP
- **OAuth2** — Autenticação segura

### Utilitários
- **python-dotenv** — Gerenciamento de variáveis de ambiente
- **Logging nativo** — Sistema de logs estruturado

---

## 🚀 Instalação e Configuração

### 1. Clone o Repositório
```bash
git clone https://github.com/seu-usuario/TotoroACDC.git
cd TotoroACDC
```

### 2. Crie um Ambiente Virtual
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Instale as Dependências
```bash
pip install -r requirements.txt
```

### 4. Configure o Banco de Dados MySQL
```sql
-- Crie um banco de dados
CREATE DATABASE bling_integration;

-- Crie um usuário (opcional)
CREATE USER 'bling_user'@'localhost' IDENTIFIED BY 'sua_senha';
GRANT ALL PRIVILEGES ON bling_integration.* TO 'bling_user'@'localhost';
FLUSH PRIVILEGES;
```

---

## 📋 Configuração do Ambiente

Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:

```env
# Configurações do Bling API v3
BLING_CLIENT_ID=seu_client_id
BLING_CLIENT_SECRET=seu_client_secret
BLING_ACCESS_TOKEN=seu_access_token
BLING_REFRESH_TOKEN=seu_refresh_token

# Configurações do MySQL
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=bling_user
MYSQL_PASSWORD=sua_senha
MYSQL_DATABASE=bling_integration

# Configurações de Logging
LOG_FILE=integracao_bling.log
LOG_LEVEL=INFO

# Configurações de Sincronização
DETAILS_MAX_AGE_HOURS=168  # 7 dias
BUSCA_LIMITE=100           # Itens por página

# Configurações do Flask
FLASK_ENV=development
FLASK_DEBUG=True
```

### Obtendo Credenciais do Bling
1. Acesse o [Portal de Desenvolvedores do Bling](https://developer.bling.com.br/)
2. Crie uma aplicação OAuth2
3. Obtenha o `client_id` e `client_secret`
4. Realize o fluxo OAuth2 para obter os tokens iniciais

---

## 💻 Como Usar

### Sincronização de Produtos
```bash
# Executa sincronização completa de produtos
python main.py
```

### Sincronização de Clientes
```bash
# Executa sincronização completa de clientes
python sincronizar_clientes.py
```

### Interface Web de Monitoramento
```bash
# Inicia o servidor web na porta 5000
python token_monitor.py
```
Acesse: http://localhost:5000

### Renovação Manual de Token
```bash
# Renova o token via linha de comando
python token_refresh.py
```

---

## 🌐 Interface Web

A interface web oferece:

- **Status em tempo real** dos tokens de acesso
- **Informações de expiração** e próxima renovação
- **Botão de renovação manual** com feedback visual
- **Design responsivo** e moderno
- **Atualizações automáticas** via JavaScript

### Recursos da Interface
- ✅ Visualização do access token atual
- ✅ Data/hora da última renovação
- ✅ Previsão da próxima renovação
- ✅ Status atual (válido/expirado)
- ✅ Renovação com um clique
- ✅ Mensagens de sucesso/erro

---

## 📊 Estrutura do Banco de Dados

### Tabela: produtos_bling
```sql
CREATE TABLE produtos_bling (
    id_bling INT PRIMARY KEY,
    codigo VARCHAR(50),
    nome VARCHAR(255),
    preco DECIMAL(10,2),
    estoque DECIMAL(10,2),
    tipo VARCHAR(50),
    situacao CHAR(1),
    formato VARCHAR(50),
    largura DECIMAL(10,3),
    altura DECIMAL(10,3),
    profundidade DECIMAL(10,3),
    peso_liquido DECIMAL(10,3),
    peso_bruto DECIMAL(10,3),
    imagem TEXT,
    data_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### Tabela: clientes_bling
```sql
CREATE TABLE clientes_bling (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(50),
    nome VARCHAR(255),
    fantasia VARCHAR(255),
    tipo CHAR(1),
    documento VARCHAR(20),
    ie VARCHAR(20),
    rg VARCHAR(20),
    telefone VARCHAR(20),
    celular VARCHAR(20),
    email VARCHAR(255),
    endereco VARCHAR(255),
    numero VARCHAR(10),
    complemento VARCHAR(100),
    bairro VARCHAR(100),
    cep VARCHAR(10),
    municipio VARCHAR(100),
    uf CHAR(2),
    situacao CHAR(1) DEFAULT 'A'
);
```

---

## 🔍 Logs e Monitoramento

### Sistema de Logging
- **Arquivo de log**: `integracao_bling.log`
- **Níveis configuráveis**: DEBUG, INFO, WARNING, ERROR
- **Formato estruturado**: timestamp, nível, mensagem
- **Saída dupla**: arquivo + console
- **Encoding UTF-8** para caracteres especiais

### Métricas Monitoradas
- ✅ Total de produtos processados
- ✅ Número de upserts realizados
- ✅ Detalhes atualizados/pulados/falhados
- ✅ Tempo de execução
- ✅ Erros e exceções
- ✅ Status dos tokens OAuth2

### Exemplo de Log
```
2024-01-15 10:30:15 - INFO - Iniciando sincronização com Bling...
2024-01-15 10:30:16 - INFO - Total de produtos encontrados na API: 1250
2024-01-15 10:30:45 - INFO - Commit realizado após processar 100 detalhes
2024-01-15 10:31:20 - WARNING - Finalizado. Processados=1250 | Upserts=1250 | Detalhes ok=980 | Detalhes pulados=200 | Detalhes falha=70
```

---

## 🤝 Contribuição

### Como Contribuir
1. **Fork** o projeto
2. Crie uma **branch** para sua feature (`git checkout -b feature/nova-funcionalidade`)
3. **Commit** suas mudanças (`git commit -am 'Adiciona nova funcionalidade'`)
4. **Push** para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um **Pull Request**

### Diretrizes
- ✅ Mantenha o código limpo e documentado
- ✅ Adicione testes para novas funcionalidades
- ✅ Siga as convenções de nomenclatura existentes
- ✅ Atualize a documentação quando necessário
- ✅ Teste em ambiente local antes de submeter

### Reportar Bugs
- Use as **Issues** do GitHub
- Inclua **logs de erro** quando possível
- Descreva **passos para reproduzir** o problema
- Especifique **versão do Python** e **sistema operacional**

---

## 📄 Licença

Este projeto está sob a licença **MIT**. Veja o arquivo `LICENSE` para mais detalhes.
---

## 🎯 Status do Desenvolvimento

- ✅ **Sincronização de Produtos** - Completo
- ✅ **Sincronização de Clientes** - Completo  
- ✅ **Gerenciamento de Tokens** - Completo
- ✅ **Interface Web** - Completo
- ✅ **Sistema de Logs** - Completo
- 🔄 **Testes Automatizados** - Em desenvolvimento
- 🔄 **Docker Support** - Planejado
- 🔄 **API REST própria** - Planejado

---

**Desenvolvido com ❤️ para automatizar integrações com Bling ERP**
