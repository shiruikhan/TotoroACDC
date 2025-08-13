# 🐾 TotoroACDC — Integração Bling ERP ↔ Site de Vendas

![Bling](https://img.shields.io/badge/Bling-ERP-green)
![Python](https://img.shields.io/badge/Python-Integration-blue)
![Status](https://img.shields.io/badge/Status-Ativo-success)

**TotoroACDC** é um projeto em **Python** que automatiza a sincronização entre o **Bling ERP** e o site de vendas. Ele faz a integração de produtos, estoque, pedidos, faturamento e logs de auditoria, eliminando tarefas manuais e garantindo consistência entre os sistemas.

---

## 📑 Sumário
1. [📂 Arquivos do Repositório](#-arquivos-do-repositório)  
2. [⚙️ Funcionalidades Principais](#️-funcionalidades-principais)  
3. [🔧 Tecnologias Utilizadas](#-tecnologias-utilizadas)  
4. [🚀 Como Utilizar](#-como-utilizar)  
5. [📌 Boas Práticas](#-boas-práticas)  
6. [🎯 Objetivos do Projeto](#-objetivos-do-projeto)

---

## 📂 Arquivos do Repositório

```
.vscode/                   → Configurações do editor
__pycache__/               → Cache do Python
bling_api.py               → Cliente para chamadas à API do Bling
token_refresh.py           → Renovação de tokens de autenticação
db.py                      → Conexão e operações com banco de dados local
detalhes_bling.py          → Detalhamento e parsing dos dados do Bling
logger.py                  → Logging estruturado da execução
main.py                    → Lógica principal da integração
integracao_bling.log       → Exemplo de log de execução
requirements.txt           → Dependências Python (pip)
```

---

## ⚙️ Funcionalidades Principais

- 🔄 **Sincronização de Produtos** — Criação, atualização e consistência entre catálogo do site e Bling.  
- 📦 **Controle de Estoque** — Atualização em tempo real das quantidades disponíveis.  
- 🛒 **Sincronização de Pedidos** — Captura pedidos do site e envia ao Bling com status e dados do cliente.  
- 💳 **Faturamento e Pagamentos** — Integração do status de pagamento ao fluxo do ERP.  
- 📈 **Logs de Auditoria** — Rastreio completo de eventos e erros via `logger.py`.

---

## 🔧 Tecnologias Utilizadas

- **Python 3.x** — base da implementação.  
- **Requests** (ou similar) — comunicação REST com a API do Bling.  
- **SQLite / PostgreSQL / MySQL** — armazenamento local temporário e logs.  
- **Logging Python** — monitoramento da execução.  
- **Git** — versionamento.  

---

## 🚀 Como Utilizar

1. Clone este repositório:
   ```bash
   git clone https://github.com/shiruikhan/TotoroACDC.git
   ```
2. Crie e ative um ambiente virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate   # Windows
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure credenciais e endpoints (variáveis de ambiente ou arquivo `.env` no `.gitignore`).  
5. Execute:
   ```bash
   python main.py
   ```

---

## 📌 Boas Práticas

- Nunca versionar credenciais — usar **variáveis de ambiente** ou `.env`.  
- Implementar **tratamento de falhas e retries** nas chamadas à API.  
- Utilizar **logs detalhados** com níveis (INFO, DEBUG, ERROR).  
- Testar em **homologação** antes de produção.  

---

## 🎯 Objetivos do Projeto

- ✅ Automatizar completamente o fluxo entre site e Bling.  
- ✅ Garantir integridade e consistência dos dados.  
- ✅ Reduzir retrabalho e erros manuais.  
- ✅ Melhorar eficiência operacional.  
- ✅ Facilitar monitoramento e auditoria via logs.  
