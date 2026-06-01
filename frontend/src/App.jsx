import React, { useState, useEffect, useRef } from 'react';
import DownloadForm from './components/DownloadForm';
import VideoInfo from './components/VideoInfo';
import QualitySelector from './components/QualitySelector';
import ProgressBar from './components/ProgressBar';
import { FaDownload, FaAndroid, FaApple, FaCopy, FaCheck, FaVideo, FaInfoCircle, FaMobileAlt, FaTimes, FaTrash, FaHistory, FaLink } from 'react-icons/fa';
import './App.css';

// API_BASE : vide = utilise la même origine (fonctionne avec ngrok, IP locale, localhost, etc.)
const API_BASE = process.env.REACT_APP_API_URL || '';

function App() {
  const [videoInfo, setVideoInfo] = useState(null);
  const [selectedFormat, setSelectedFormat] = useState(null);
  const [downloadProgress, setDownloadProgress] = useState(null);
  const [downloadStatus, setDownloadStatus] = useState('idle'); // 'idle' | 'starting' | 'downloading' | 'processing' | 'completed' | 'error'
  const [taskId, setTaskId] = useState(null);
  const [completedTask, setCompletedTask] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [linkCopied, setLinkCopied] = useState(false);
  const [currentUrl, setCurrentUrl] = useState('');
  const [history, setHistory] = useState([]);
  
  const [deferredPrompt, setDeferredPrompt] = useState(null);
  const [showInstallPrompt, setShowInstallPrompt] = useState(false);
  const [isIos, setIsIos] = useState(false);
  const [isAlreadyInstalled, setIsAlreadyInstalled] = useState(false);
  
  const pollingRef = useRef(null);

  // Charger l'historique sur mount
  useEffect(() => {
    const saved = localStorage.getItem('download_history');
    if (saved) {
      try {
        setHistory(JSON.parse(saved));
      } catch (e) {
        console.error("Erreur de chargement de l'historique", e);
      }
    }
  }, []);

  // Nettoyage de l'intervalle lors du démontage du composant
  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, []);

  // Gestion de l'installation de la PWA
  useEffect(() => {
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches 
      || window.navigator.standalone 
      || document.referrer.includes('android-app://');
    
    setIsAlreadyInstalled(isStandalone);

    const ios = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
    setIsIos(ios);

    const handleBeforeInstallPrompt = (e) => {
      e.preventDefault();
      setDeferredPrompt(e);
      setShowInstallPrompt(true);
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);

    // Sur iOS, afficher la bannière si l'application n'est pas déjà installée (en standalone)
    if (ios && !isStandalone) {
      setShowInstallPrompt(true);
    }

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    };
  }, []);

  const handleInstallClick = async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    console.log(`PWA Install choice: ${outcome}`);
    setDeferredPrompt(null);
    setShowInstallPrompt(false);
  };

  const handleUrlSubmit = async (url) => {
    setCurrentUrl(url);
    setLoading(true);
    setError(null);
    setVideoInfo(null);
    setSelectedFormat(null);
    setDownloadProgress(null);
    setTaskId(null);
    setDownloadStatus('idle');
    setCompletedTask(null);
    
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
    }
    
    try {
      const response = await fetch(`${API_BASE}/api/info`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
      });
      
      const data = await response.json();
      
      if (data.success) {
        setVideoInfo(data);
      } else {
        setError(data.error);
      }
    } catch (err) {
      setError('Erreur de connexion au serveur (assurez-vous que le backend est démarré)');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    setLoading(true);
    setError(null);
    setDownloadProgress(0);
    setDownloadStatus('starting');
    setCompletedTask(null);
    
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
    }
    
    try {
      const response = await fetch(`${API_BASE}/api/download`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: videoInfo?.url || currentUrl,
          format_id: selectedFormat?.format_id
        })
      });
      
      const data = await response.json();
      
      if (!data.success || !data.task_id) {
        throw new Error(data.error || 'Erreur lors du démarrage du téléchargement');
      }
      
      setTaskId(data.task_id);
      setDownloadStatus('downloading');
      
      // Polling du statut
      pollingRef.current = setInterval(async () => {
        try {
          const statusResponse = await fetch(
            `${API_BASE}/api/download/${data.task_id}`
          );
          const statusData = await statusResponse.json();
          
          if (!statusData.success) {
            clearInterval(pollingRef.current);
            setError(statusData.error || 'Erreur de récupération du statut.');
            setLoading(false);
            setDownloadStatus('error');
            return;
          }
          
          setDownloadProgress(statusData.progress);
          setDownloadStatus(statusData.status);
          
          if (statusData.status === 'completed') {
            clearInterval(pollingRef.current);
            
            const task = {
              taskId: data.task_id,
              filename: statusData.filename,
              title: statusData.title || videoInfo.title,
              size: statusData.size,
              platform: statusData.platform || videoInfo.platform,
              downloadedAt: new Date().toISOString(),
              sourceUrl: videoInfo?.url || currentUrl,
            };

            setCompletedTask(task);

            // Sauvegarder dans l'historique localStorage
            setHistory(prev => {
              const updated = [task, ...prev].slice(0, 50); // Garder max 50 entrées
              localStorage.setItem('download_history', JSON.stringify(updated));
              return updated;
            });
            
            setLoading(false);
            
            // Lancer le téléchargement automatique uniquement sur PC/Mac
            const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
            if (!isMobile) {
              window.location.href = `${API_BASE}/api/download/${data.task_id}/file`;
            }
          } else if (statusData.status === 'error') {
            clearInterval(pollingRef.current);
            setError(statusData.error);
            setLoading(false);
            setDownloadStatus('error');
          }
        } catch (err) {
          clearInterval(pollingRef.current);
          setError('Erreur lors du suivi du téléchargement');
          setLoading(false);
          setDownloadStatus('error');
        }
      }, 1000);
    } catch (err) {
      setError(err.message || 'Erreur lors du téléchargement');
      setLoading(false);
      setDownloadStatus('error');
    }
  };

  const handleCopyLink = () => {
    if (!completedTask) return;
    const downloadUrl = `${API_BASE}/api/download/${completedTask.taskId}/file`;
    navigator.clipboard.writeText(downloadUrl);
    setLinkCopied(true);
    setTimeout(() => setLinkCopied(false), 2000);
  };

  const formatSize = (bytes) => {
    if (!bytes || isNaN(bytes)) return 'inconnue';
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(2)} Mo`;
  };

  const getDownloadUrl = (taskId) => {
    return `${API_BASE}/api/download/${taskId}/file`;
  };

  const clearHistory = () => {
    localStorage.removeItem('download_history');
    setHistory([]);
  };

  const formatDate = (iso) => {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const getPlatformEmoji = (platform) => {
    const map = { youtube: '▶️', tiktok: '🎵', instagram: '📸', facebook: '📘', twitter: '🐦', vimeo: '🎬', twitch: '🟣', reddit: '🔴' };
    return map[platform] || '🌐';
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>📥 HenoBuild Downloader All Videos</h1>
        <p>Téléchargez vos vidéos YouTube, TikTok, Instagram et plus encore</p>
      </header>

      <main className="app-main">
        {showInstallPrompt && !isAlreadyInstalled && (
          <div className="install-banner">
            <div className="install-banner-main">
              <div className="install-icon-wrapper">
                <FaMobileAlt />
              </div>
              <div className="install-info">
                <h4>Installer l'application</h4>
                <p>Ajoutez l'appli sur votre écran d'accueil pour un accès ultra-rapide et l'utiliser hors ligne.</p>
              </div>
              {isIos ? (
                <div className="ios-install-badge">
                  <FaInfoCircle /> Partager 📤 puis "Sur l'écran d'accueil"
                </div>
              ) : (
                <button className="install-btn-pwa" onClick={handleInstallClick}>
                  Installer
                </button>
              )}
            </div>
            <button className="install-close-btn" onClick={() => setShowInstallPrompt(false)}>
              <FaTimes />
            </button>
          </div>
        )}
        
        <DownloadForm onSubmit={handleUrlSubmit} loading={loading} />
        
        {error && (
          <div className="error-message">
            <p>{error}</p>
          </div>
        )}
        
        {videoInfo && !completedTask && (
          <div className="video-details">
            <VideoInfo info={videoInfo} />
            <QualitySelector
              formats={videoInfo.formats}
              onSelect={setSelectedFormat}
              selected={selectedFormat}
            />
            <button
              className="download-btn"
              onClick={handleDownload}
              disabled={loading}
            >
              {loading ? (
                downloadStatus === 'starting' ? 'Initialisation...' :
                downloadStatus === 'processing' ? 'Fusion en cours...' :
                'Téléchargement...'
              ) : '📥 Démarrer le téléchargement'}
            </button>
          </div>
        )}
        
        {downloadProgress !== null && !completedTask && (
          <ProgressBar progress={downloadProgress} status={downloadStatus} />
        )}

        {completedTask && (
          <div className="completed-card">
            <div className="completed-header">
              <span className="success-badge">✓ Prêt</span>
              <h2>Vidéo préparée avec succès !</h2>
            </div>
            
            <div className="completed-info">
              <div className="completed-title">
                <FaVideo /> {completedTask.title}
              </div>
              <div className="completed-meta">
                <span>Taille : <strong>{formatSize(completedTask.size)}</strong></span>
                <span>Format : <strong>{completedTask.filename ? completedTask.filename.split('.').pop().toUpperCase() : 'MP4'}</strong></span>
              </div>
            </div>

            <div className="download-methods">
              <h3>Options de téléchargement :</h3>
              
              <div className="methods-grid">
                {/* Option PC / Standard */}
                <div className="method-box standard">
                  <h4>💻 Ordinateur (PC / Mac)</h4>
                  <p>Téléchargement direct dans votre dossier Téléchargements.</p>
                  <a href={getDownloadUrl(completedTask.taskId)} download className="method-btn button-standard">
                    <FaDownload /> Télécharger la vidéo
                  </a>
                </div>

                {/* Option Android */}
                <div className="method-box android">
                  <h4>🤖 Téléphone Android</h4>
                  <p>Démarre le téléchargement dans le navigateur de votre smartphone.</p>
                  <a href={getDownloadUrl(completedTask.taskId)} target="_blank" rel="noopener noreferrer" className="method-btn button-android">
                    <FaAndroid /> Télécharger sur Android
                  </a>
                </div>

                {/* Option iOS */}
                <div className="method-box ios">
                  <h4>🍏 iPhone / iPad (iOS)</h4>
                  <p>Ouvre la vidéo dans Safari pour l'enregistrer dans vos fichiers.</p>
                  <a href={getDownloadUrl(completedTask.taskId)} target="_blank" rel="noopener noreferrer" className="method-btn button-ios">
                    <FaApple /> Ouvrir pour iOS
                  </a>
                  <div className="ios-instructions">
                    <FaInfoCircle />
                    <span>
                      <strong>Méthode Safari :</strong> Après ouverture, appuyez sur l'icône de partage 📤 puis sélectionnez <strong>"Enregistrer dans Fichiers"</strong>.
                    </span>
                  </div>
                </div>
              </div>

              <div className="method-footer">
                <button className="copy-link-btn" onClick={handleCopyLink}>
                  {linkCopied ? (
                    <>
                      <FaCheck /> Lien copié !
                    </>
                  ) : (
                    <>
                      <FaCopy /> Copier le lien de téléchargement
                    </>
                  )}
                </button>
              </div>
            </div>
            
            <button 
              className="reset-btn" 
              onClick={() => {
                setCompletedTask(null);
                setVideoInfo(null);
                setSelectedFormat(null);
                setDownloadProgress(null);
                setTaskId(null);
                setDownloadStatus('idle');
              }}
            >
              Télécharger une autre vidéo
            </button>
          </div>
        )}

        {/* Historique des téléchargements */}
        {history.length > 0 && (
          <div className="history-section">
            <div className="history-header">
              <h3><FaHistory /> Historique des téléchargements</h3>
              <button className="history-clear-btn" onClick={clearHistory}>
                <FaTrash /> Effacer
              </button>
            </div>
            <ul className="history-list">
              {history.map((item, idx) => (
                <li key={idx} className="history-item">
                  <div className="history-item-icon">{getPlatformEmoji(item.platform)}</div>
                  <div className="history-item-info">
                    <div className="history-item-title">{item.title || item.filename || 'Vidéo'}</div>
                    <div className="history-item-meta">
                      <span>{formatDate(item.downloadedAt)}</span>
                      {item.size && <span>{formatSize(item.size)}</span>}
                    </div>
                  </div>
                  <a
                    href={getDownloadUrl(item.taskId)}
                    className="history-download-btn"
                    title="Re-télécharger"
                  >
                    <FaLink />
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;