@echo off
chcp 65001 > nul
cd /d "%~dp0"
title HenoBuild Video Downloader - Demarrage

echo.
echo ========================================================
echo   HenoBuild Video Downloader - Demarrage complet
echo ========================================================
echo.

:: Verifier si Python est installe
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Python n'est pas installe ou pas dans le PATH.
    echo Telechargez Python sur https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Choix du mode d'acces tunnel
echo Choisissez l'option d'acces au projet :
echo   1. Mode Internet (Via Serveo - Recommande, aucun compte requis)
echo   2. Mode Internet (Via Pinggy - Alternative, aucun compte requis)
echo   3. Mode Local uniquement (Accessible sur votre PC et reseau local)
echo.
set /p option="Entrez votre choix (1, 2 ou 3) [Defaut: 1] : "

if "%option%"=="" set option=1

if "%option%"=="1" (
    echo [INFO] Demarrage du tunnel public Serveo sur le port 5000...
    start "Tunnel Public (Serveo)" cmd /k "ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=60 -R 80:127.0.0.1:5000 serveo.net"
    goto start_backend
)
if "%option%"=="2" (
    echo [INFO] Demarrage du tunnel public Pinggy sur le port 5000...
    start "Tunnel Public (Pinggy)" cmd /k "ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=60 -R 80:127.0.0.1:5000 free@pinggy.io"
    goto start_backend
)
if "%option%"=="3" (
    echo [INFO] Lancement en mode local uniquement...
    goto start_backend
)

:start_backend
:: Installer les dependances Python si necessaire
echo [INFO] Verification des dependances Python...
cd /d "%~dp0backend"
pip install -r requirements.txt --user -q

echo.
echo [INFO] Demarrage du serveur backend sur le port 5000...
echo [INFO] L'application est disponible sur :
echo         - Local     : http://localhost:5000
echo         - Reseau    : http://%COMPUTERNAME%:5000
echo         - Internet  : Voir la fenetre du Tunnel ouverte
echo.
echo [CONSEIL] Partagez le lien HTTPS de la fenetre de tunnel pour que tout le monde y accede !
echo.

:: Demarrer le backend Flask
python app.py

pause
