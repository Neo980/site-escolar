@echo off
REM ============================================================
REM  Gera o MerendaNaMedida.exe (rodar este script no Windows,
REM  dentro da pasta do projeto, com o ambiente virtual ativado)
REM ============================================================

echo Instalando as dependencias do projeto (Flask etc.)...
python -m pip install -r requirements.txt

echo Instalando PyInstaller...
python -m pip install pyinstaller

echo.
echo Conferindo se o Flask esta disponivel neste Python...
python -c "import flask" 2>NUL
if errorlevel 1 goto SEM_FLASK
echo Flask encontrado, prosseguindo...
goto SEGUE

:SEM_FLASK
echo.
echo ============================================================
echo ERRO: O Flask nao foi encontrado neste Python.
echo O .exe NAO vai funcionar se continuar assim.
echo Verifique se o ambiente virtual .venv esta ativado antes de
echo rodar este script - o inicio da linha do terminal deve
echo mostrar .venv entre parenteses.
echo ============================================================
pause
exit /b 1

:SEGUE

echo.
echo Gerando o executavel...

if exist static (
    python -m PyInstaller --onefile --noupx --name MerendaNaMedida ^
        --add-data "templates;templates" ^
        --add-data "static;static" ^
        app.py
) else (
    python -m PyInstaller --onefile --noupx --name MerendaNaMedida ^
        --add-data "templates;templates" ^
        app.py
)

echo.
echo ============================================================
echo Pronto! O executavel esta em: dist\MerendaNaMedida.exe
echo Copie esse arquivo para onde quiser rodar o sistema.
echo Na primeira vez que for aberto, ele cria o merenda.db do
echo lado dele automaticamente.
echo ============================================================
pause
