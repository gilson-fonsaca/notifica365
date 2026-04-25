#!/bin/bash

# Aborta o script em caso de erro
set -e

echo "🚀 Iniciando processo de build do Notifica365..."

# Verifica se o ambiente virtual existe, se não, cria
if [ ! -d ".venv" ]; then
    echo "📦 Criando ambiente virtual (.venv)..."
    python3 -m venv .venv
fi

# Ativa o ambiente virtual
echo "🔄 Ativando ambiente virtual..."
source .venv/bin/activate

# Instala as dependências normais do projeto
echo "📚 Instalando dependências do projeto (requirements.txt)..."
pip install -r requirements.txt

# Instala o PyInstaller para gerar o binário
echo "🛠️ Instalando PyInstaller..."
pip install pyinstaller

# Limpa builds anteriores (opcional, mas recomendado)
echo "🧹 Limpando arquivos de builds anteriores..."
rm -rf build/ dist/ *.spec

# Compila o script python em um único arquivo binário executável (--onefile)
echo "⚙️ Compilando o binário..."
pyinstaller --name notifica365 --onefile notifica.py

echo "🔄 Copiando arquivo .env para o binário..."
cp .env dist/.env

# Desativa o ambiente virtual
deactivate

echo "✅ Build concluído com sucesso!"
echo "O seu binário executável está pronto e localizado em: ./dist/notifica365"
