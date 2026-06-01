import yt_dlp
import os
import re
import json
from datetime import datetime
import requests
from urllib.parse import urlparse, parse_qs
import subprocess
import tempfile
import random

class VideoDownloader:
    def __init__(self):
        self.output_dir = "downloads"
        
        # Liste d'User-Agents pour rotation
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36'
        ]
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def get_random_user_agent(self):
        """Retourne un User-Agent aléatoire"""
        return random.choice(self.user_agents)

    def detect_platform(self, url):
        """Détecte la plateforme de la vidéo"""
        url_lower = url.lower()
        
        platforms = {
            'youtube.com': 'youtube',
            'youtu.be': 'youtube',
            'tiktok.com': 'tiktok',
            'instagram.com': 'instagram',
            'facebook.com': 'facebook',
            'fb.watch': 'facebook',
            'twitter.com': 'twitter',
            'x.com': 'twitter',
            'vimeo.com': 'vimeo',
            'dailymotion.com': 'dailymotion',
            'twitch.tv': 'twitch',
            'reddit.com': 'reddit',
            'linkedin.com': 'linkedin',
            'pinterest.com': 'pinterest',
            'snapchat.com': 'snapchat',
            'likee.com': 'likee',
            'kwai.com': 'kwai',
            'bilibili.com': 'bilibili',
            'rumble.com': 'rumble',
            'odysee.com': 'odysee',
            'bitchute.com': 'bitchute'
        }
        
        for domain, platform in platforms.items():
            if domain in url_lower:
                return platform
        
        return 'other'

    def create_advanced_options(self, platform, format_id=None):
        """Crée des options avancées pour le téléchargement"""
        
        # Headers sophistiqués avec rotation d'User-Agent
        custom_headers = {
            'User-Agent': self.get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7,de;q=0.6,es;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://www.google.com/',
            'Origin': 'https://www.google.com',
            'DNT': '1',
            'Connection': 'keep-alive',
        }
        
        # Options de base optimisées
        ydl_opts = {
            'http_headers': custom_headers,
            'quiet': False,
            'no_warnings': False,
            'verbose': False,
            'extract_flat': False,
            'force_generic_extractor': False,
            'no_check_certificate': True,
            'prefer_insecure': True,
            'geo_bypass': True,
            'geo_bypass_country': random.choice(['US', 'FR', 'DE', 'UK', 'CA', 'JP', 'NL']),
            'geo_bypass_ip_block': True,
            'socket_timeout': 60,
            'retries': 20,
            'fragment_retries': 20,
            'retry_sleep': lambda n: min(2 ** n, 30),
            'ignoreerrors': False,
            'no_color': True,
            'cachedir': False,
            'rm_cachedir': True,
            'writethumbnail': False,
            'writeinfojson': False,
            'windowsfilenames': True,
            'restrictfilenames': False,
            'trim_file_name': 200,
            'concurrent_fragment_downloads': 16,
            'buffersize': 32768,
            'http_chunk_size': 10485760,
            'sleep_interval_requests': random.uniform(0.5, 2),
            'max_sleep_interval_requests': 5,
            'sleep_interval_subtitles': 1,
            'extractor_retries': 10,
        }
        
        # Options spécifiques selon la plateforme
        if platform == 'youtube':
            ydl_opts.update({
                'format': 'bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/best[height<=2160][ext=mp4]/bestvideo+bestaudio/best',
                'format_sort': ['res:2160', 'codec:h264:aac', 'size', 'br'],
                'youtube_include_dash_manifest': True,
                'youtube_include_hls_manifest': True,
                'extractor_args': {
                    'youtube': {
                        'skip': [],
                        'player_skip': [],
                        'player_client': ['android', 'ios', 'web', 'tv', 'web_safari'],
                        'include_live_dash': True,
                        'include_live_audio_formats': True,
                        'max_comments': 0,
                    }
                },
                'postprocessor_args': {
                    'ffmpeg': ['-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k']
                }
            })
            
            if format_id:
                ydl_opts['format'] = f'{format_id}+bestaudio/best'
                
        elif platform == 'tiktok':
            ydl_opts.update({
                'format': 'best',
                'extractor_args': {
                    'tiktok': {
                        'api_hostname': [
                            'api16-normal-c-useast1a.tiktokv.com',
                            'api.tiktokv.com',
                            'api19-normal-c-useast2a.tiktokv.com'
                        ],
                        'app_info': {
                            'app_version': '32.1.3',
                            'manifest_app_version': '32.1.3',
                            'aid': '1988'
                        }
                    }
                }
            })
            
        elif platform == 'instagram':
            ydl_opts.update({
                'format': 'best',
                'extractor_args': {
                    'instagram': {
                        'include_thumbnail': False,
                        'app_id': '936619743392459',
                        'app_secret': '30e9c8a3bb7f4e4b3b9b1a0f4d3c5e6a'
                    }
                }
            })
            
        elif platform in ['facebook', 'twitter']:
            ydl_opts.update({
                'format': 'bestvideo+bestaudio/best',
            })
            
        elif platform == 'twitch':
            ydl_opts.update({
                'format': 'best',
                'extractor_args': {
                    'twitch': {
                        'client_id': 'kimne78kx3ncx6brgo4mv6wki5h1ko'
                    }
                }
            })
            
        else:
            ydl_opts.update({
                'format': 'bestvideo+bestaudio/best',
                'extract_flat': False,
                'force_generic_extractor': False,
            })
        
        return ydl_opts

    def get_video_info(self, url):
        """Récupère les informations de la vidéo"""
        platform = self.detect_platform(url)
        
        # Plusieurs tentatives avec différentes configurations
        configs = [
            self.create_advanced_options(platform),
            {
                'format': 'best',
                'quiet': True,
                'no_warnings': True,
                'geo_bypass': True,
                'no_check_certificate': True,
                'force_generic_extractor': True,
            },
            {
                'format': 'worst',
                'quiet': True,
                'no_warnings': True,
                'geo_bypass': True,
                'no_check_certificate': True,
                'extract_flat': True,
            }
        ]
        
        last_error = None
        
        for idx, ydl_opts in enumerate(configs):
            try:
                ydl_opts.update({
                    'dump_single_json': False,
                })
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                    formats = []
                    all_formats = info.get('formats', [])
                    
                    for f in all_formats:
                        if f.get('vcodec') != 'none' or f.get('acodec') != 'none':
                            format_info = {
                                'format_id': f.get('format_id') or '',
                                'quality': f.get('quality_label') or f.get('format_note') or 'Unknown',
                                'ext': f.get('ext') or 'mp4',
                                'filesize': f.get('filesize') if f.get('filesize') is not None else 0,
                                'filesize_approx': f.get('filesize_approx') if f.get('filesize_approx') is not None else 0,
                                'resolution': f.get('resolution') or 'Unknown',
                                'fps': f.get('fps') if f.get('fps') is not None else 0,
                                'codec': f.get('vcodec') or 'unknown',
                                'audio_codec': f.get('acodec') or 'unknown',
                                'has_audio': f.get('acodec') != 'none' and f.get('acodec') is not None,
                                'has_video': f.get('vcodec') != 'none' and f.get('vcodec') is not None,
                                'tbr': f.get('tbr') if f.get('tbr') is not None else 0,
                                'abr': f.get('abr') if f.get('abr') is not None else 0,
                                'vbr': f.get('vbr') if f.get('vbr') is not None else 0,
                                'width': f.get('width') if f.get('width') is not None else 0,
                                'height': f.get('height') if f.get('height') is not None else 0,
                                'protocol': f.get('protocol') or '',
                            }
                            formats.append(format_info)
                    
                    # Trier par qualité
                    formats.sort(key=lambda x: (
                        x.get('height') if x.get('height') is not None else 0,
                        x.get('fps') if x.get('fps') is not None else 0,
                        x.get('tbr') if x.get('tbr') is not None else 0
                    ), reverse=True)
                    
                    return {
                        'success': True,
                        'platform': platform,
                        'title': info.get('title', 'Sans titre'),
                        'description': info.get('description', ''),
                        'duration': info.get('duration', 0),
                        'thumbnail': info.get('thumbnail', ''),
                        'uploader': info.get('uploader', 'Inconnu'),
                        'upload_date': info.get('upload_date', ''),
                        'view_count': info.get('view_count', 0),
                        'like_count': info.get('like_count', 0),
                        'formats': formats[:25],
                        'subtitles': list(info.get('subtitles', {}).keys()),
                        'age_limit': info.get('age_limit', 0),
                        'is_live': info.get('is_live', False),
                        'was_live': info.get('was_live', False),
                    }
                    
            except Exception as e:
                last_error = str(e)
                continue
        
        # Si toutes les tentatives échouent
        return {
            'success': False,
            'error': f'Impossible d\'accéder à cette vidéo après plusieurs tentatives. Erreur: {last_error}'
        }

    def download_video(self, url, format_id=None, progress_callback=None, quality='best'):
        """Télécharge la vidéo avec le format spécifié"""
        platform = self.detect_platform(url)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        output_template = os.path.join(
            self.output_dir,
            f'%(title)s_{timestamp}.%(ext)s'
        )

        def progress_hook(d):
            if progress_callback:
                if d['status'] == 'downloading':
                    total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                    if not isinstance(total, (int, float)):
                        total = 0
                    downloaded = d.get('downloaded_bytes') or 0
                    if not isinstance(downloaded, (int, float)):
                        downloaded = 0
                    if total > 0:
                        progress = (downloaded / total) * 100
                        speed = d.get('speed') or 0
                        if not isinstance(speed, (int, float)):
                            speed = 0
                        eta = d.get('eta') or 0
                        if not isinstance(eta, (int, float)):
                            eta = 0
                        
                        progress_callback({
                            'progress': progress,
                            'speed': speed,
                            'downloaded': downloaded,
                            'total': total,
                            'eta': eta,
                            'filename': d.get('filename', ''),
                            'status': 'downloading'
                        })
                elif d['status'] == 'finished':
                    progress_callback({
                        'progress': 100,
                        'status': 'processing',
                        'filename': d.get('filename', '')
                    })

        # Configuration de base
        ydl_opts = self.create_advanced_options(platform, format_id)
        
        # Ajuster la qualité
        if quality == 'best':
            ydl_opts['format'] = 'bestvideo+bestaudio/best'
        elif quality == 'worst':
            ydl_opts['format'] = 'worst'
        elif format_id:
            ydl_opts['format'] = format_id
        
        ydl_opts.update({
            'outtmpl': output_template,
            'progress_hooks': [progress_hook],
            'merge_output_format': 'mp4',
            'prefer_ffmpeg': True,
            'keepvideo': False,
            'writethumbnail': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'allsubtitles': False,
            'subtitleslangs': ['fr', 'en'],
        })

        # Multiples tentatives avec différentes approches
        download_methods = [
            # Méthode 1: Configuration standard
            lambda: self._attempt_download(ydl_opts, url, progress_callback),
            
            # Méthode 2: Extraction générique forcée
            lambda: self._force_generic_download(url, output_template, progress_callback),
            
            # Méthode 3: Utilisation directe de yt-dlp en ligne de commande
            lambda: self._cli_download(url, output_template, platform, progress_callback),
        ]
        
        last_error = None
        for method in download_methods:
            try:
                result = method()
                if result and result.get('success'):
                    return result
            except Exception as e:
                last_error = str(e)
                continue
        
        return {
            'success': False,
            'error': f'Échec du téléchargement après toutes les tentatives: {last_error}'
        }

    def _attempt_download(self, ydl_opts, url, progress_callback):
        """Tentative de téléchargement avec options yt-dlp"""
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            # Trouver le fichier réel
            actual_file = self._find_downloaded_file(filename)
            
            if actual_file and progress_callback:
                progress_callback({
                    'progress': 100,
                    'status': 'completed',
                    'filename': os.path.basename(actual_file),
                    'title': info.get('title', 'Sans titre'),
                    'path': actual_file
                })
            
            return {
                'success': True,
                'filename': os.path.basename(actual_file) if actual_file else filename,
                'title': info.get('title', 'Sans titre'),
                'path': actual_file or filename,
                'size': os.path.getsize(actual_file) if actual_file else 0,
                'platform': self.detect_platform(url)
            }

    def _force_generic_download(self, url, output_template, progress_callback):
        """Téléchargement avec extracteur générique forcé"""
        opts = {
            'format': 'best',
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'force_generic_extractor': True,
            'no_check_certificate': True,
            'geo_bypass': True,
            'user_agent': self.get_random_user_agent(),
        }
        
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            actual_file = self._find_downloaded_file(filename)
            
            return {
                'success': True,
                'filename': os.path.basename(actual_file) if actual_file else filename,
                'title': info.get('title', 'Sans titre'),
                'path': actual_file or filename,
                'size': os.path.getsize(actual_file) if actual_file else 0,
                'platform': self.detect_platform(url)
            }

    def _cli_download(self, url, output_template, platform, progress_callback):
        """Téléchargement via ligne de commande yt-dlp"""
        import subprocess
        
        cmd = [
            'yt-dlp',
            '--format', 'bestvideo+bestaudio/best',
            '--output', output_template,
            '--user-agent', self.get_random_user_agent(),
            '--geo-bypass',
            '--no-check-certificate',
            '--no-playlist',
            '--merge-output-format', 'mp4',
            url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            # Chercher le fichier téléchargé
            for root, dirs, files in os.walk(self.output_dir):
                for file in files:
                    if file.endswith(('.mp4', '.webm', '.mkv')):
                        filepath = os.path.join(root, file)
                        return {
                            'success': True,
                            'filename': file,
                            'title': file,
                            'path': filepath,
                            'size': os.path.getsize(filepath),
                            'platform': platform
                        }
        
        raise Exception(f"CLI download failed: {result.stderr}")

    def _find_downloaded_file(self, base_filename):
        """Trouve le fichier réellement téléchargé"""
        base = os.path.splitext(base_filename)[0]
        
        for ext in ['mp4', 'webm', 'mkv', 'flv', 'avi', 'mov', 'm4a', 'mp3']:
            test_file = f"{base}.{ext}"
            if os.path.exists(test_file):
                return test_file
        
        # Chercher avec un motif plus large
        dir_name = os.path.dirname(base_filename)
        base_name = os.path.basename(base)
        
        if os.path.exists(dir_name):
            for file in os.listdir(dir_name):
                if file.startswith(base_name) and file.split('.')[-1] in ['mp4', 'webm', 'mkv', 'flv', 'avi', 'mov']:
                    return os.path.join(dir_name, file)
        
        return None

    def download_playlist(self, url, progress_callback=None):
        """Télécharge une playlist entière"""
        platform = self.detect_platform(url)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        playlist_dir = os.path.join(self.output_dir, f'playlist_{timestamp}')
        if not os.path.exists(playlist_dir):
            os.makedirs(playlist_dir)
        
        output_template = os.path.join(playlist_dir, '%(playlist_index)s - %(title)s.%(ext)s')
        
        ydl_opts = self.create_advanced_options(platform)
        ydl_opts.update({
            'outtmpl': output_template,
            'ignoreerrors': True,
            'playliststart': 1,
            'playlistend': 100,
            'concurrent_fragment_downloads': 8,
        })
        
        if progress_callback:
            ydl_opts['progress_hooks'] = [progress_callback]
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                downloaded_files = []
                for entry in info.get('entries', []):
                    if entry:
                        downloaded_files.append({
                            'title': entry.get('title'),
                            'filename': ydl.prepare_filename(entry)
                        })
                
                return {
                    'success': True,
                    'playlist_title': info.get('title', 'Playlist'),
                    'total_videos': len(info.get('entries', [])),
                    'downloaded_files': downloaded_files,
                    'directory': playlist_dir
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Erreur téléchargement playlist: {str(e)}'
            }

    def download_audio_only(self, url, progress_callback=None):
        """Télécharge uniquement l'audio d'une vidéo"""
        platform = self.detect_platform(url)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        output_template = os.path.join(
            self.output_dir,
            f'%(title)s_{timestamp}.%(ext)s'
        )
        
        ydl_opts = self.create_advanced_options(platform)
        ydl_opts.update({
            'format': 'bestaudio/best',
            'outtmpl': output_template,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
        
        if progress_callback:
            ydl_opts['progress_hooks'] = [progress_callback]
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                # Ajuster l'extension pour mp3
                mp3_file = filename.rsplit('.', 1)[0] + '.mp3'
                
                return {
                    'success': True,
                    'filename': os.path.basename(mp3_file),
                    'title': info.get('title', 'Sans titre'),
                    'path': mp3_file,
                    'size': os.path.getsize(mp3_file) if os.path.exists(mp3_file) else 0,
                    'platform': platform
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Erreur téléchargement audio: {str(e)}'
            }