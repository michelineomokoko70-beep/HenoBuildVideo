from flask import Flask, request, jsonify, send_file, Response, stream_with_context, send_from_directory
from flask_cors import CORS
from utils.downloader import VideoDownloader
import threading
import uuid
import os
import json
import time
import shutil
import zipfile
import io
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import re
import traceback

# Déterminer le chemin absolu du dossier de build React
frontend_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '../frontend/build'))
app = Flask(__name__, static_folder=frontend_folder, static_url_path='/')
# Configuration CORS plus permissive pour le développement
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Configuration de l'application
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max request size
app.config['DOWNLOAD_FOLDER'] = 'downloads'
app.config['TEMP_FOLDER'] = 'temp'
app.config['CLEANUP_INTERVAL'] = 3600  # 1 heure
app.config['MAX_TASK_AGE'] = 7200  # 2 heures

# Création des dossiers nécessaires
for folder in [app.config['DOWNLOAD_FOLDER'], app.config['TEMP_FOLDER']]:
    if not os.path.exists(folder):
        os.makedirs(folder)

downloader = VideoDownloader()
download_tasks = {}
active_downloads = {}  # Pour limiter les téléchargements simultanés
download_queue = []  # File d'attente pour les téléchargements

# Limites de téléchargement
MAX_CONCURRENT_DOWNLOADS = 3
MAX_DOWNLOADS_PER_IP = 5
RATE_LIMIT_WINDOW = 3600  # 1 heure

# Statistiques
stats = {
    'total_downloads': 0,
    'successful_downloads': 0,
    'failed_downloads': 0,
    'total_bytes_downloaded': 0,
    'start_time': time.time()
}

class DownloadTask:
    """Classe pour gérer une tâche de téléchargement"""
    def __init__(self, task_id, url, options=None):
        self.task_id = task_id
        self.url = url
        self.options = options or {}
        self.status = 'queued'
        self.progress = 0
        self.speed = 0
        self.downloaded = 0
        self.total = 0
        self.eta = 0
        self.result = None
        self.error = None
        self.created_at = time.time()
        self.started_at = None
        self.completed_at = None
        self.client_ip = None
        self.platform = None
        self.filename = None
        self.filepath = None
        self.filesize = 0
        
    def to_dict(self):
        """Convertit la tâche en dictionnaire pour l'API"""
        # S'assurer que toutes les valeurs sont sérialisables
        result_title = None
        if self.result and isinstance(self.result, dict):
            result_title = self.result.get('title')
        
        # Calculer le pourcentage de progression en toute sécurité
        progress_percent = 0
        if isinstance(self.progress, (int, float)):
            progress_percent = self.progress
        elif isinstance(self.progress, str):
            try:
                progress_percent = float(self.progress)
            except (ValueError, TypeError):
                progress_percent = 0
        
        # S'assurer que les valeurs numériques sont valides
        speed_val = self.speed if isinstance(self.speed, (int, float)) and self.speed is not None else 0
        downloaded_val = self.downloaded if isinstance(self.downloaded, (int, float)) and self.downloaded is not None else 0
        total_val = self.total if isinstance(self.total, (int, float)) and self.total is not None else 0
        eta_val = self.eta if isinstance(self.eta, (int, float)) and self.eta is not None else 0
        filesize_val = self.filesize if isinstance(self.filesize, (int, float)) and self.filesize is not None else 0
        
        return {
            'task_id': self.task_id,
            'url': self.url,
            'status': self.status,
            'progress': progress_percent,
            'speed': speed_val,
            'downloaded': downloaded_val,
            'total': total_val,
            'eta': eta_val,
            'filename': self.filename,
            'title': result_title,
            'size': filesize_val,
            'platform': self.platform,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'error': self.error
        }

def get_client_ip():
    """Récupère l'IP du client en toute sécurité"""
    try:
        if request and request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        if request:
            return request.remote_addr or '127.0.0.1'
    except:
        pass
    return '127.0.0.1'

def check_rate_limit(ip):
    """Vérifie les limites de téléchargement par IP"""
    if not ip:
        return True
    
    current_time = time.time()
    ip_downloads = 0
    
    try:
        for task in download_tasks.values():
            if hasattr(task, 'client_ip') and task.client_ip == ip:
                if hasattr(task, 'created_at') and task.created_at:
                    task_age = current_time - task.created_at
                    if task_age < RATE_LIMIT_WINDOW:
                        ip_downloads += 1
    except Exception as e:
        print(f"Erreur vérification rate limit: {e}")
        return True  # En cas d'erreur, autoriser le téléchargement
    
    return ip_downloads < MAX_DOWNLOADS_PER_IP

def process_download_queue():
    """Traite la file d'attente des téléchargements"""
    try:
        while download_queue and len(active_downloads) < MAX_CONCURRENT_DOWNLOADS:
            task = download_queue.pop(0)
            start_download_thread(task)
    except Exception as e:
        print(f"Erreur traitement file d'attente: {e}")

def start_download_thread(task):
    """Démarre le thread de téléchargement"""
    if not task or not hasattr(task, 'task_id'):
        return
    
    task.status = 'preparing'
    task.started_at = time.time()
    active_downloads[task.task_id] = task
    
    def progress_callback(progress_data):
        try:
            if not progress_data or not isinstance(progress_data, dict):
                return
            
            # Mise à jour sécurisée des propriétés
            progress = progress_data.get('progress')
            if progress is not None:
                task.progress = float(progress) if isinstance(progress, (int, float, str)) else 0
            
            speed = progress_data.get('speed')
            if speed is not None:
                task.speed = float(speed) if isinstance(speed, (int, float, str)) else 0
            
            downloaded = progress_data.get('downloaded')
            if downloaded is not None:
                task.downloaded = int(downloaded) if isinstance(downloaded, (int, float, str)) else 0
            
            total = progress_data.get('total')
            if total is not None:
                task.total = int(total) if isinstance(total, (int, float, str)) else 0
            
            eta = progress_data.get('eta')
            if eta is not None:
                task.eta = int(eta) if isinstance(eta, (int, float, str)) else 0
            
            filename = progress_data.get('filename')
            if filename:
                task.filename = str(filename)
            
            status = progress_data.get('status')
            if status == 'completed':
                task.status = 'processing'
            elif status == 'error':
                task.status = 'error'
                task.error = progress_data.get('error', 'Erreur inconnue')
        except Exception as e:
            print(f"Erreur dans progress_callback: {e}")
    
    def run_download():
        try:
            if not hasattr(task, 'options'):
                task.options = {}
            
            is_playlist = task.options.get('is_playlist', False)
            format_id = task.options.get('format_id')
            quality = task.options.get('quality', 'best')
            audio_only = task.options.get('audio_only', False)
            
            result = None
            
            if is_playlist:
                result = downloader.download_playlist(task.url, progress_callback)
            elif audio_only:
                result = downloader.download_audio_only(task.url, progress_callback)
            else:
                result = downloader.download_video(
                    task.url,
                    format_id=format_id,
                    progress_callback=progress_callback,
                    quality=quality
                )
            
            if result and isinstance(result, dict):
                task.result = result
                
                if result.get('success'):
                    task.status = 'completed'
                    task.filename = result.get('filename')
                    task.filepath = result.get('path')
                    task.filesize = result.get('size', 0)
                    if not isinstance(task.filesize, (int, float)):
                        task.filesize = 0
                    task.platform = result.get('platform')
                    stats['successful_downloads'] += 1
                    stats['total_bytes_downloaded'] += task.filesize
                else:
                    task.status = 'error'
                    task.error = result.get('error', 'Erreur inconnue')
                    stats['failed_downloads'] += 1
            else:
                task.status = 'error'
                task.error = 'Résultat de téléchargement invalide'
                stats['failed_downloads'] += 1
            
            task.completed_at = time.time()
            
        except Exception as e:
            task.status = 'error'
            task.error = str(e)
            task.completed_at = time.time()
            stats['failed_downloads'] += 1
            print(f"Erreur téléchargement: {traceback.format_exc()}")
        
        finally:
            # Nettoyer la tâche active
            if task.task_id in active_downloads:
                del active_downloads[task.task_id]
            stats['total_downloads'] += 1
            
            # Traiter la file d'attente
            process_download_queue()
    
    thread = threading.Thread(target=run_download)
    thread.daemon = True
    thread.start()

# Nettoyage périodique des anciennes tâches et fichiers
def cleanup_scheduler():
    """Planificateur de nettoyage"""
    while True:
        time.sleep(app.config['CLEANUP_INTERVAL'])
        try:
            cleanup_old_tasks()
            cleanup_old_files()
        except Exception as e:
            print(f"Erreur de nettoyage: {e}")

def cleanup_old_tasks():
    """Nettoie les anciennes tâches de la mémoire"""
    current_time = time.time()
    to_delete = []
    
    try:
        for task_id, task in list(download_tasks.items()):
            if hasattr(task, 'created_at') and task.created_at:
                task_age = current_time - task.created_at
                if task_age > app.config['MAX_TASK_AGE']:
                    to_delete.append(task_id)
        
        for task_id in to_delete:
            task = download_tasks.get(task_id)
            if task and hasattr(task, 'filepath') and task.filepath:
                if os.path.exists(task.filepath):
                    try:
                        os.remove(task.filepath)
                    except:
                        pass
            if task_id in download_tasks:
                del download_tasks[task_id]
    except Exception as e:
        print(f"Erreur nettoyage tâches: {e}")

def cleanup_old_files():
    """Nettoie les anciens fichiers téléchargés"""
    current_time = time.time()
    max_age = 24 * 3600  # 24 heures par défaut
    
    for folder in [app.config['DOWNLOAD_FOLDER'], app.config['TEMP_FOLDER']]:
        if os.path.exists(folder):
            try:
                for filename in os.listdir(folder):
                    filepath = os.path.join(folder, filename)
                    if os.path.isfile(filepath):
                        try:
                            file_age = current_time - os.path.getctime(filepath)
                            if file_age > max_age:
                                os.remove(filepath)
                        except (OSError, IOError) as e:
                            print(f"Erreur suppression fichier {filepath}: {e}")
            except Exception as e:
                print(f"Erreur lecture dossier {folder}: {e}")

# Servir l'application React (build de production)
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    """Sert le frontend React buildé ou redirige vers index.html pour le routing SPA"""
    if path.startswith('api/'):
        return jsonify({'success': False, 'error': 'Endpoint non trouvé'}), 404
    
    if app.static_folder and os.path.exists(os.path.join(app.static_folder, path)) and path != '':
        return send_from_directory(app.static_folder, path)
    
    index_path = os.path.join(app.static_folder, 'index.html') if app.static_folder else None
    if index_path and os.path.exists(index_path):
        return send_from_directory(app.static_folder, 'index.html')
    
    return jsonify({
        'status': 'online',
        'service': 'HenoBuild Video Downloader API',
        'version': '2.0.0',
        'note': 'Frontend non compilé. Lancez: cd frontend && npm run build',
        'endpoints': ['/api/info', '/api/download', '/api/platforms', '/api/stats']
    })

@app.route('/api/info', methods=['POST'])
def get_video_info():
    """Endpoint pour obtenir les informations complètes de la vidéo"""
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'Données JSON requises'}), 400
            
        url = data.get('url')
        
        if not url:
            return jsonify({'success': False, 'error': 'URL requise'}), 400
        
        # Valider l'URL
        if not re.match(r'^https?://', url):
            return jsonify({'success': False, 'error': 'URL invalide. Doit commencer par http:// ou https://'}), 400
        
        # Vérifier si l'URL est trop longue
        if len(url) > 2000:
            return jsonify({'success': False, 'error': 'URL trop longue'}), 400
        
        info = downloader.get_video_info(url)
        
        # S'assurer que info est un dictionnaire
        if not isinstance(info, dict):
            return jsonify({
                'success': False,
                'error': 'Format de réponse invalide'
            }), 500
        
        # Ajouter des métadonnées supplémentaires
        if info.get('success'):
            info['url'] = url
            info['requested_at'] = datetime.now().isoformat()
            info['platform'] = downloader.detect_platform(url)
            
            # Calculer la taille estimée pour chaque format en toute sécurité
            formats = info.get('formats', [])
            if isinstance(formats, list):
                for format in formats:
                    if isinstance(format, dict):
                        filesize = format.get('filesize')
                        if filesize and isinstance(filesize, (int, float)):
                            format['filesize_mb'] = round(filesize / (1024 * 1024), 2)
                        else:
                            format['filesize_mb'] = 0
                        
                        filesize_approx = format.get('filesize_approx')
                        if filesize_approx and isinstance(filesize_approx, (int, float)):
                            format['filesize_approx_mb'] = round(filesize_approx / (1024 * 1024), 2)
                        else:
                            format['filesize_approx_mb'] = 0
        
        return jsonify(info)
        
    except Exception as e:
        print(f"Erreur /api/info: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'Erreur serveur: {str(e)}'
        }), 500

@app.route('/api/download', methods=['POST'])
def start_download():
    """Endpoint pour démarrer un téléchargement"""
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'Données JSON requises'}), 400
            
        url = data.get('url')
        format_id = data.get('format_id')
        quality = data.get('quality', 'best')
        is_playlist = data.get('is_playlist', False)
        audio_only = data.get('audio_only', False)
        
        if not url:
            return jsonify({'success': False, 'error': 'URL requise'}), 400
        
        # Valider l'URL
        if not re.match(r'^https?://', url):
            return jsonify({'success': False, 'error': 'URL invalide'}), 400
        
        # Vérifier les limites par IP
        client_ip = get_client_ip()
        if not check_rate_limit(client_ip):
            return jsonify({
                'success': False,
                'error': f'Limite de {MAX_DOWNLOADS_PER_IP} téléchargements par heure atteinte'
            }), 429
        
        # Créer la tâche
        task_id = str(uuid.uuid4())
        task = DownloadTask(task_id, url, options={
            'format_id': format_id,
            'quality': quality,
            'is_playlist': is_playlist,
            'audio_only': audio_only
        })
        task.client_ip = client_ip
        task.platform = downloader.detect_platform(url)
        
        download_tasks[task_id] = task
        
        # Mettre en file d'attente ou démarrer directement
        if len(active_downloads) < MAX_CONCURRENT_DOWNLOADS:
            start_download_thread(task)
        else:
            download_queue.append(task)
            task.status = 'queued'
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'status': task.status,
            'position': len(download_queue) if task.status == 'queued' else 0
        })
        
    except Exception as e:
        print(f"Erreur /api/download: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'Erreur démarrage téléchargement: {str(e)}'
        }), 500

@app.route('/api/download/<task_id>', methods=['GET'])
def get_download_status(task_id):
    """Endpoint pour vérifier l'état du téléchargement"""
    try:
        task = download_tasks.get(task_id)
        if not task:
            return jsonify({'success': False, 'error': 'Tâche non trouvée'}), 404
        
        return jsonify({
            'success': True,
            **task.to_dict()
        })
    except Exception as e:
        print(f"Erreur statut téléchargement: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'Erreur récupération statut: {str(e)}'
        }), 500

@app.route('/api/download/<task_id>/cancel', methods=['POST'])
def cancel_download(task_id):
    """Annule un téléchargement en cours"""
    try:
        task = download_tasks.get(task_id)
        if not task:
            return jsonify({'success': False, 'error': 'Tâche non trouvée'}), 404
        
        if task.status in ['completed', 'error']:
            return jsonify({'success': False, 'error': 'Téléchargement déjà terminé'}), 400
        
        task.status = 'cancelled'
        if task_id in active_downloads:
            del active_downloads[task_id]
        
        # Traiter la file d'attente
        process_download_queue()
        
        return jsonify({
            'success': True,
            'message': 'Téléchargement annulé'
        })
    except Exception as e:
        print(f"Erreur annulation: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'Erreur annulation: {str(e)}'
        }), 500

@app.route('/api/download/<task_id>/file', methods=['GET'])
def download_file(task_id):
    """Endpoint pour télécharger le fichier final"""
    try:
        task = download_tasks.get(task_id)
        if not task:
            return jsonify({'success': False, 'error': 'Tâche non trouvée'}), 404
        
        if task.status != 'completed':
            return jsonify({'success': False, 'error': 'Téléchargement non terminé'}), 400
        
        filepath = task.filepath
        if not filepath or not os.path.exists(filepath):
            return jsonify({'success': False, 'error': 'Fichier non trouvé sur le disque'}), 404
        
        filename = task.filename or 'video.mp4'
        
        # Déterminer le type MIME
        mimetypes = {
            'mp4': 'video/mp4',
            'webm': 'video/webm',
            'mkv': 'video/x-matroska',
            'mp3': 'audio/mpeg',
            'm4a': 'audio/mp4',
            'flv': 'video/x-flv',
            'avi': 'video/x-msvideo',
            'mov': 'video/quicktime'
        }
        
        # Extraire l'extension en toute sécurité
        ext = 'mp4'
        if filename and '.' in filename:
            ext = filename.rsplit('.', 1)[-1].lower()
        
        mimetype = mimetypes.get(ext, 'application/octet-stream')
        
        # Obtenir la taille du fichier en toute sécurité
        try:
            file_size = os.path.getsize(filepath)
        except:
            file_size = 0
        
        # Streaming du fichier pour les gros fichiers
        def generate():
            try:
                with open(filepath, 'rb') as f:
                    while True:
                        chunk = f.read(8192)  # 8KB chunks
                        if not chunk:
                            break
                        yield chunk
            except Exception as e:
                print(f"Erreur streaming fichier: {e}")
        
        safe_filename = secure_filename(filename) if filename else 'video.mp4'
        
        response = Response(
            stream_with_context(generate()),
            mimetype=mimetype,
            headers={
                'Content-Disposition': f'attachment; filename="{safe_filename}"',
                'Content-Length': str(file_size),
                'Cache-Control': 'no-cache',
                'X-Content-Type-Options': 'nosniff',
                'Access-Control-Expose-Headers': 'Content-Disposition, Content-Length'
            }
        )
        
        return response
        
    except Exception as e:
        print(f"Erreur téléchargement fichier: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'Erreur récupération fichier: {str(e)}'
        }), 500

@app.route('/api/downloads', methods=['GET'])
def list_downloads():
    """Liste tous les téléchargements avec pagination"""
    try:
        status_filter = request.args.get('status')
        page = int(request.args.get('page', 1) or 1)
        per_page = min(int(request.args.get('per_page', 20) or 20), 100)
        
        # S'assurer que page est au moins 1
        if page < 1:
            page = 1
        
        tasks = list(download_tasks.values())
        
        # Filtrer par statut
        if status_filter:
            tasks = [t for t in tasks if hasattr(t, 'status') and t.status == status_filter]
        
        # Trier par date de création (plus récent d'abord)
        tasks.sort(key=lambda x: x.created_at if hasattr(x, 'created_at') and x.created_at else 0, reverse=True)
        
        # Pagination
        total = len(tasks)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_tasks = tasks[start:end]
        
        # Calculer le nombre total de pages
        total_pages = (total + per_page - 1) // per_page if per_page > 0 else 1
        
        return jsonify({
            'success': True,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': total_pages,
            'downloads': [task.to_dict() for task in paginated_tasks]
        })
    except Exception as e:
        print(f"Erreur liste téléchargements: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'Erreur récupération liste: {str(e)}'
        }), 500

@app.route('/api/batch', methods=['POST'])
def batch_download():
    """Téléchargement par lot de plusieurs URLs"""
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'Données JSON requises'}), 400
            
        urls = data.get('urls', [])
        
        if not urls or not isinstance(urls, list):
            return jsonify({'success': False, 'error': 'Liste d\'URLs requise'}), 400
        
        if len(urls) > 10:
            return jsonify({'success': False, 'error': 'Maximum 10 URLs par lot'}), 400
        
        task_ids = []
        for url in urls:
            if not isinstance(url, str) or not re.match(r'^https?://', url):
                continue
                
            task_id = str(uuid.uuid4())
            task = DownloadTask(task_id, url)
            task.client_ip = get_client_ip()
            task.platform = downloader.detect_platform(url)
            
            download_tasks[task_id] = task
            
            if len(active_downloads) < MAX_CONCURRENT_DOWNLOADS:
                start_download_thread(task)
            else:
                download_queue.append(task)
                task.status = 'queued'
            
            task_ids.append(task_id)
        
        return jsonify({
            'success': True,
            'task_ids': task_ids,
            'total': len(task_ids)
        })
        
    except Exception as e:
        print(f"Erreur batch: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'Erreur traitement batch: {str(e)}'
        }), 500

@app.route('/api/platforms', methods=['GET'])
def get_supported_platforms():
    """Retourne les plateformes supportées"""
    platforms = [
        {'name': 'YouTube', 'code': 'youtube', 'icon': 'youtube', 'features': ['video', 'audio', 'playlist', 'subtitles']},
        {'name': 'TikTok', 'code': 'tiktok', 'icon': 'tiktok', 'features': ['video']},
        {'name': 'Instagram', 'code': 'instagram', 'icon': 'instagram', 'features': ['video', 'image']},
        {'name': 'Facebook', 'code': 'facebook', 'icon': 'facebook', 'features': ['video']},
        {'name': 'Twitter/X', 'code': 'twitter', 'icon': 'twitter', 'features': ['video']},
        {'name': 'Vimeo', 'code': 'vimeo', 'icon': 'vimeo', 'features': ['video', 'audio']},
        {'name': 'Dailymotion', 'code': 'dailymotion', 'icon': 'dailymotion', 'features': ['video']},
        {'name': 'Twitch', 'code': 'twitch', 'icon': 'twitch', 'features': ['video', 'clip']},
        {'name': 'Reddit', 'code': 'reddit', 'icon': 'reddit', 'features': ['video']},
        {'name': 'LinkedIn', 'code': 'linkedin', 'icon': 'linkedin', 'features': ['video']},
        {'name': 'Pinterest', 'code': 'pinterest', 'icon': 'pinterest', 'features': ['video', 'image']},
        {'name': 'Snapchat', 'code': 'snapchat', 'icon': 'snapchat', 'features': ['video']},
        {'name': 'Bilibili', 'code': 'bilibili', 'icon': 'bilibili', 'features': ['video']},
        {'name': 'Rumble', 'code': 'rumble', 'icon': 'rumble', 'features': ['video']},
        {'name': 'Odysee', 'code': 'odysee', 'icon': 'odysee', 'features': ['video']},
        {'name': 'Autres sites', 'code': 'other', 'icon': 'globe', 'features': ['video']}
    ]
    
    return jsonify({
        'success': True,
        'platforms': platforms,
        'total': len(platforms)
    })

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Retourne les statistiques du serveur"""
    try:
        current_time = time.time()
        uptime = current_time - stats['start_time']
        
        # Calculer le taux de succès en toute sécurité
        total_downloads = max(stats['total_downloads'], 1)
        success_rate = (stats['successful_downloads'] / total_downloads * 100)
        
        return jsonify({
            'success': True,
            'stats': {
                'uptime_seconds': int(uptime),
                'uptime_formatted': str(timedelta(seconds=int(uptime))),
                'total_downloads': stats['total_downloads'],
                'successful_downloads': stats['successful_downloads'],
                'failed_downloads': stats['failed_downloads'],
                'success_rate': f"{success_rate:.1f}%",
                'total_bytes_downloaded': stats['total_bytes_downloaded'],
                'total_gb_downloaded': f"{stats['total_bytes_downloaded'] / (1024**3):.2f}",
                'active_downloads': len(active_downloads),
                'queued_downloads': len(download_queue),
                'max_concurrent': MAX_CONCURRENT_DOWNLOADS,
                'total_tasks_in_memory': len(download_tasks)
            }
        })
    except Exception as e:
        print(f"Erreur statistiques: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'Erreur récupération statistiques: {str(e)}'
        }), 500

@app.route('/api/cleanup', methods=['POST'])
def manual_cleanup():
    """Nettoie manuellement les anciens téléchargements"""
    try:
        data = request.json or {}
        max_age_hours = float(data.get('max_age_hours', 24) or 24)
        clean_tasks = data.get('clean_tasks', True)
        clean_files = data.get('clean_files', True)
        
        deleted_files = 0
        freed_space = 0
        deleted_tasks = 0
        
        # Nettoyer les fichiers
        if clean_files:
            current_time = time.time()
            for folder in [app.config['DOWNLOAD_FOLDER'], app.config['TEMP_FOLDER']]:
                if os.path.exists(folder):
                    try:
                        for filename in os.listdir(folder):
                            filepath = os.path.join(folder, filename)
                            if os.path.isfile(filepath):
                                try:
                                    file_age = current_time - os.path.getctime(filepath)
                                    if file_age > (max_age_hours * 3600):
                                        file_size = os.path.getsize(filepath)
                                        os.remove(filepath)
                                        deleted_files += 1
                                        freed_space += file_size
                                except (OSError, IOError) as e:
                                    print(f"Erreur suppression {filepath}: {e}")
                    except Exception as e:
                        print(f"Erreur lecture dossier {folder}: {e}")
        
        # Nettoyer les tâches en mémoire
        if clean_tasks:
            current_time = time.time()
            for task_id, task in list(download_tasks.items()):
                if hasattr(task, 'created_at') and task.created_at:
                    task_age = current_time - task.created_at
                    if task_age > (max_age_hours * 3600):
                        del download_tasks[task_id]
                        deleted_tasks += 1
        
        return jsonify({
            'success': True,
            'deleted_files': deleted_files,
            'freed_space_mb': round(freed_space / (1024 * 1024), 2) if freed_space > 0 else 0,
            'deleted_tasks': deleted_tasks,
            'message': f'{deleted_files} fichiers et {deleted_tasks} tâches supprimés'
        })
        
    except Exception as e:
        print(f"Erreur nettoyage: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/formats', methods=['GET'])
def get_common_formats():
    """Retourne les formats de téléchargement courants"""
    formats = [
        {'id': 'best', 'label': 'Meilleure qualité', 'description': 'Sélectionne automatiquement la meilleure qualité disponible'},
        {'id': '1080p', 'label': 'Full HD (1080p)', 'description': 'Vidéo en 1920x1080'},
        {'id': '720p', 'label': 'HD (720p)', 'description': 'Vidéo en 1280x720'},
        {'id': '480p', 'label': 'SD (480p)', 'description': 'Vidéo en 854x480'},
        {'id': '360p', 'label': 'Basse qualité (360p)', 'description': 'Vidéo en 640x360'},
        {'id': 'audio', 'label': 'Audio uniquement', 'description': 'Extrait uniquement la piste audio en MP3'}
    ]
    
    return jsonify({
        'success': True,
        'formats': formats
    })

# Gestionnaires d'erreurs
@app.errorhandler(404)
def not_found(error):
    # Pour les routes non-API, servir le React app
    if app.static_folder:
        index_path = os.path.join(app.static_folder, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(app.static_folder, 'index.html')
    return jsonify({'success': False, 'error': 'Endpoint non trouvé'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'error': 'Erreur interne du serveur'}), 500

@app.errorhandler(429)
def rate_limit_error(error):
    return jsonify({'success': False, 'error': 'Trop de requêtes. Veuillez réessayer plus tard.'}), 429

@app.errorhandler(Exception)
def handle_exception(error):
    """Gestionnaire global d'exceptions"""
    print(f"Exception non gérée: {traceback.format_exc()}")
    return jsonify({
        'success': False,
        'error': 'Erreur interne du serveur'
    }), 500

if __name__ == '__main__':
    # Démarrer le thread de nettoyage
    cleanup_thread = threading.Thread(target=cleanup_scheduler)
    cleanup_thread.daemon = True
    cleanup_thread.start()
    
    # Configuration du serveur
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    print(f"""
    Serveur de téléchargement vidéo démarré!
    Adresse: http://0.0.0.0:{port}
    Endpoints disponibles:
       - GET  /api/platforms    : Plateformes supportées
       - POST /api/info         : Informations vidéo
       - POST /api/download     : Démarrer un téléchargement
       - GET  /api/download/:id : Statut du téléchargement
       - GET  /api/download/:id/file : Télécharger le fichier
       - POST /api/batch        : Téléchargement par lot
       - GET  /api/stats        : Statistiques
       - POST /api/cleanup      : Nettoyage manuel
    """)
    
    app.run(
        debug=debug,
        host='0.0.0.0',
        port=port,
        threaded=True,
        processes=1
    )