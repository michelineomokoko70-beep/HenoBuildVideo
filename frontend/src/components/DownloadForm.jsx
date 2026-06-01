import React, { useState, useEffect, useRef } from 'react';
import { 
  FaYoutube, FaTiktok, FaInstagram, FaFacebook, 
  FaTwitter, FaVimeo, FaReddit, FaTwitch,
  FaLinkedin, FaPinterest, FaGlobe, FaSnapchat,
  FaDownload, FaList, FaVideo, FaTimes, FaLink,
  FaSpinner, FaCheck, FaExclamationTriangle
} from 'react-icons/fa';

function DownloadForm({ onSubmit, loading }) {
  const [url, setUrl] = useState('');
  const [isPlaylist, setIsPlaylist] = useState(false);
  const [error, setError] = useState('');
  const [isValid, setIsValid] = useState(false);
  const [detectedPlatform, setDetectedPlatform] = useState(null);
  const [urlHistory, setUrlHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const inputRef = useRef(null);

  // Charger l'historique depuis le localStorage
  useEffect(() => {
    try {
      const saved = localStorage.getItem('urlHistory');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed)) {
          setUrlHistory(parsed.slice(0, 10)); // Garder les 10 dernières
        }
      }
    } catch (e) {
      console.error('Erreur chargement historique:', e);
    }
  }, []);

  // Validation de l'URL
  useEffect(() => {
    validateUrl(url);
  }, [url]);

  const validateUrl = (value) => {
    if (!value || !value.trim()) {
      setError('');
      setIsValid(false);
      setDetectedPlatform(null);
      return;
    }

    const trimmedUrl = value.trim();

    // Vérifier le format de base de l'URL
    const urlPattern = /^https?:\/\/.+/i;
    if (!urlPattern.test(trimmedUrl)) {
      setError('L\'URL doit commencer par http:// ou https://');
      setIsValid(false);
      setDetectedPlatform(null);
      return;
    }

    // Vérifier si l'URL est trop courte
    if (trimmedUrl.length < 10) {
      setError('URL trop courte');
      setIsValid(false);
      setDetectedPlatform(null);
      return;
    }

    // Détecter la plateforme
    const platform = detectPlatform(trimmedUrl);
    setDetectedPlatform(platform);

    if (!platform) {
      setError('Plateforme non reconnue. Vérifiez votre lien.');
      setIsValid(false);
      return;
    }

    setError('');
    setIsValid(true);
  };

  const detectPlatform = (urlString) => {
    if (!urlString || typeof urlString !== 'string') return null;
    
    const urlLower = urlString.toLowerCase();
    
    const platforms = {
      youtube: ['youtube.com', 'youtu.be', 'm.youtube.com', 'music.youtube.com'],
      tiktok: ['tiktok.com', 'vm.tiktok.com', 'vt.tiktok.com'],
      instagram: ['instagram.com', 'instagr.am'],
      facebook: ['facebook.com', 'fb.watch', 'fb.com', 'm.facebook.com'],
      twitter: ['twitter.com', 'x.com', 't.co'],
      vimeo: ['vimeo.com', 'player.vimeo.com'],
      twitch: ['twitch.tv', 'm.twitch.tv', 'clips.twitch.tv'],
      reddit: ['reddit.com', 'redd.it', 'old.reddit.com'],
      linkedin: ['linkedin.com', 'lnkd.in'],
      pinterest: ['pinterest.com', 'pin.it'],
      snapchat: ['snapchat.com'],
      dailymotion: ['dailymotion.com'],
      bilibili: ['bilibili.com'],
      rumble: ['rumble.com'],
      odysee: ['odysee.com']
    };

    for (const [platform, domains] of Object.entries(platforms)) {
      if (domains.some(domain => urlLower.includes(domain))) {
        return platform;
      }
    }

    // Si l'URL contient un domaine générique de vidéo
    if (/\.(mp4|webm|mkv|avi|mov|flv|m3u8)(\?.*)?$/i.test(urlLower)) {
      return 'direct';
    }

    return null;
  };

  const getPlatformIcon = (platform) => {
    const icons = {
      youtube: <FaYoutube className="icon youtube" />,
      tiktok: <FaTiktok className="icon tiktok" />,
      instagram: <FaInstagram className="icon instagram" />,
      facebook: <FaFacebook className="icon facebook" />,
      twitter: <FaTwitter className="icon twitter" />,
      vimeo: <FaVimeo className="icon vimeo" />,
      twitch: <FaTwitch className="icon twitch" />,
      reddit: <FaReddit className="icon reddit" />,
      linkedin: <FaLinkedin className="icon linkedin" />,
      pinterest: <FaPinterest className="icon pinterest" />,
      snapchat: <FaSnapchat className="icon snapchat" />,
      direct: <FaVideo className="icon direct" />,
      other: <FaGlobe className="icon other" />
    };

    return icons[platform] || icons.other;
  };

  const getPlatformName = (platform) => {
    const names = {
      youtube: 'YouTube',
      tiktok: 'TikTok',
      instagram: 'Instagram',
      facebook: 'Facebook',
      twitter: 'Twitter / X',
      vimeo: 'Vimeo',
      twitch: 'Twitch',
      reddit: 'Reddit',
      linkedin: 'LinkedIn',
      pinterest: 'Pinterest',
      snapchat: 'Snapchat',
      dailymotion: 'Dailymotion',
      bilibili: 'Bilibili',
      rumble: 'Rumble',
      odysee: 'Odysee',
      direct: 'Vidéo directe'
    };

    return names[platform] || 'Site web';
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    
    const trimmedUrl = url.trim();
    
    if (!trimmedUrl) {
      setError('Veuillez entrer une URL');
      return;
    }

    if (!isValid) {
      setError('URL invalide. Veuillez vérifier votre lien.');
      return;
    }

    // Sauvegarder dans l'historique
    saveToHistory(trimmedUrl);
    
    // Appeler la fonction de soumission
    if (onSubmit) {
      onSubmit(trimmedUrl, isPlaylist);
    }
  };

  const saveToHistory = (urlString) => {
    try {
      const newHistory = [urlString, ...urlHistory.filter(u => u !== urlString)].slice(0, 10);
      setUrlHistory(newHistory);
      localStorage.setItem('urlHistory', JSON.stringify(newHistory));
    } catch (e) {
      console.error('Erreur sauvegarde historique:', e);
    }
  };

  const clearUrl = () => {
    setUrl('');
    setError('');
    setIsValid(false);
    setDetectedPlatform(null);
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  const pasteFromClipboard = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        setUrl(text.trim());
      }
    } catch (e) {
      console.error('Erreur accès presse-papier:', e);
      // Fallback: focus sur l'input pour collage manuel
      if (inputRef.current) {
        inputRef.current.focus();
      }
    }
  };

  const selectFromHistory = (historyUrl) => {
    setUrl(historyUrl);
    setShowHistory(false);
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  const clearHistory = () => {
    setUrlHistory([]);
    localStorage.removeItem('urlHistory');
    setShowHistory(false);
  };

  return (
    <form className="download-form" onSubmit={handleSubmit}>
      <div className="platform-icons">
        {[
          { icon: <FaYoutube />, name: 'youtube' },
          { icon: <FaTiktok />, name: 'tiktok' },
          { icon: <FaInstagram />, name: 'instagram' },
          { icon: <FaFacebook />, name: 'facebook' },
          { icon: <FaTwitter />, name: 'twitter' },
          { icon: <FaVimeo />, name: 'vimeo' },
          { icon: <FaTwitch />, name: 'twitch' },
          { icon: <FaReddit />, name: 'reddit' }
        ].map((platform, index) => (
          <span 
            key={index} 
            className={`icon-wrapper ${detectedPlatform === platform.name ? 'active' : ''}`}
            title={getPlatformName(platform.name)}
          >
            {platform.icon}
          </span>
        ))}
      </div>
      
      <div className="input-group">
        <div className={`url-input-wrapper ${isValid ? 'valid' : ''} ${error ? 'error' : ''}`}>
          <div className="input-icon">
            {detectedPlatform ? getPlatformIcon(detectedPlatform) : <FaLink />}
          </div>
          
          <input
            ref={inputRef}
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="Collez votre lien vidéo ici..."
            disabled={loading}
            className={url ? 'has-content' : ''}
            autoComplete="off"
            spellCheck="false"
          />
          
          <div className="input-actions">
            {url && !loading && (
              <button 
                type="button" 
                className="icon-btn clear-btn"
                onClick={clearUrl}
                title="Effacer"
              >
                <FaTimes />
              </button>
            )}
            
            {!url && (
              <button 
                type="button" 
                className="icon-btn paste-btn"
                onClick={pasteFromClipboard}
                title="Coller depuis le presse-papier"
              >
                <FaLink />
              </button>
            )}
          </div>
        </div>
        
        <button 
          type="submit" 
          disabled={loading || !url.trim() || !isValid}
          className={`submit-btn ${loading ? 'loading' : ''}`}
        >
          {loading ? (
            <>
              <FaSpinner className="spinner" /> Analyse en cours...
            </>
          ) : (
            <>
              <FaDownload /> Analyser
            </>
          )}
        </button>
      </div>
      
      {/* Message d'erreur */}
      {error && (
        <div className="error-message">
          <FaExclamationTriangle />
          <span>{error}</span>
        </div>
      )}
      
      {/* Info plateforme détectée */}
      {detectedPlatform && isValid && !error && (
        <div className="platform-detected">
          <FaCheck className="check-icon" />
          <span>
            Plateforme détectée : <strong>{getPlatformName(detectedPlatform)}</strong>
          </span>
        </div>
      )}
      
      <div className="options-row">
        <div className="playlist-option">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={isPlaylist}
              onChange={(e) => setIsPlaylist(e.target.checked)}
              disabled={loading}
            />
            <FaList /> Playlist (YouTube)
          </label>
        </div>
        
        {urlHistory.length > 0 && (
          <div className="history-option">
            <button
              type="button"
              className="text-btn"
              onClick={() => setShowHistory(!showHistory)}
            >
              🕐 Historique ({urlHistory.length})
            </button>
          </div>
        )}
      </div>
      
      {/* Historique des URLs */}
      {showHistory && urlHistory.length > 0 && (
        <div className="url-history">
          <div className="history-header">
            <span>URLs récentes</span>
            <button 
              type="button" 
              className="text-btn"
              onClick={clearHistory}
            >
              Tout effacer
            </button>
          </div>
          <ul className="history-list">
            {urlHistory.map((historyUrl, index) => (
              <li 
                key={index}
                onClick={() => selectFromHistory(historyUrl)}
                className="history-item"
              >
                <span className="history-icon">
                  {getPlatformIcon(detectPlatform(historyUrl))}
                </span>
                <span className="history-url" title={historyUrl}>
                  {historyUrl.length > 60 
                    ? historyUrl.substring(0, 60) + '...' 
                    : historyUrl
                  }
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <style>{`
        .download-form {
          max-width: 800px;
          margin: 0 auto;
          padding: 20px;
          background: #ffffff;
          border-radius: 16px;
          box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        }

        .platform-icons {
          display: flex;
          justify-content: center;
          gap: 15px;
          margin-bottom: 25px;
          flex-wrap: wrap;
        }

        .icon-wrapper {
          font-size: 28px;
          color: #999;
          transition: all 0.3s ease;
          cursor: pointer;
          padding: 8px;
          border-radius: 12px;
        }

        .icon-wrapper:hover {
          transform: translateY(-3px);
          color: #666;
        }

        .icon-wrapper.active {
          color: #4a90e2;
          background: rgba(74, 144, 226, 0.1);
          transform: scale(1.1);
        }

        .icon-wrapper .youtube:hover, .icon-wrapper.active .youtube { color: #FF0000; }
        .icon-wrapper .tiktok:hover, .icon-wrapper.active .tiktok { color: #000000; }
        .icon-wrapper .instagram:hover, .icon-wrapper.active .instagram { color: #E4405F; }
        .icon-wrapper .facebook:hover, .icon-wrapper.active .facebook { color: #1877F2; }
        .icon-wrapper .twitter:hover, .icon-wrapper.active .twitter { color: #1DA1F2; }
        .icon-wrapper .vimeo:hover, .icon-wrapper.active .vimeo { color: #1AB7EA; }
        .icon-wrapper .twitch:hover, .icon-wrapper.active .twitch { color: #9146FF; }
        .icon-wrapper .reddit:hover, .icon-wrapper.active .reddit { color: #FF4500; }

        .input-group {
          display: flex;
          gap: 12px;
          margin-bottom: 15px;
        }

        .url-input-wrapper {
          flex: 1;
          display: flex;
          align-items: center;
          background: #f5f5f5;
          border: 2px solid #e0e0e0;
          border-radius: 12px;
          padding: 0 15px;
          transition: all 0.3s ease;
        }

        .url-input-wrapper:focus-within {
          border-color: #4a90e2;
          background: #ffffff;
          box-shadow: 0 0 0 3px rgba(74, 144, 226, 0.1);
        }

        .url-input-wrapper.valid {
          border-color: #4caf50;
        }

        .url-input-wrapper.error {
          border-color: #f44336;
          background: #fff5f5;
        }

        .input-icon {
          font-size: 20px;
          margin-right: 10px;
          color: #999;
          min-width: 24px;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .url-input-wrapper input {
          flex: 1;
          border: none;
          background: transparent;
          padding: 15px 0;
          font-size: 16px;
          outline: none;
          color: #333;
        }

        .url-input-wrapper input::placeholder {
          color: #999;
        }

        .input-actions {
          display: flex;
          gap: 5px;
          margin-left: 10px;
        }

        .icon-btn {
          background: none;
          border: none;
          cursor: pointer;
          padding: 5px;
          color: #999;
          font-size: 16px;
          transition: all 0.3s ease;
          border-radius: 50%;
          width: 30px;
          height: 30px;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .icon-btn:hover {
          background: #e0e0e0;
          color: #333;
        }

        .submit-btn {
          padding: 15px 30px;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          border: none;
          border-radius: 12px;
          font-size: 16px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s ease;
          white-space: nowrap;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .submit-btn:hover:not(:disabled) {
          transform: translateY(-2px);
          box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        }

        .submit-btn:disabled {
          background: #ccc;
          cursor: not-allowed;
          transform: none;
        }

        .submit-btn.loading {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          cursor: wait;
        }

        .spinner {
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        .error-message {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 15px;
          background: #fff5f5;
          border: 1px solid #f44336;
          border-radius: 8px;
          color: #f44336;
          font-size: 14px;
          margin-bottom: 15px;
        }

        .platform-detected {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 15px;
          background: #f0f9f0;
          border: 1px solid #4caf50;
          border-radius: 8px;
          color: #2e7d32;
          font-size: 14px;
          margin-bottom: 15px;
        }

        .check-icon {
          color: #4caf50;
          font-size: 16px;
        }

        .options-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          flex-wrap: wrap;
          gap: 10px;
        }

        .checkbox-label {
          display: flex;
          align-items: center;
          gap: 8px;
          cursor: pointer;
          color: #666;
          font-size: 14px;
          user-select: none;
        }

        .checkbox-label input[type="checkbox"] {
          width: 18px;
          height: 18px;
          cursor: pointer;
        }

        .text-btn {
          background: none;
          border: none;
          color: #667eea;
          cursor: pointer;
          font-size: 14px;
          padding: 5px 10px;
          border-radius: 6px;
          transition: all 0.3s ease;
        }

        .text-btn:hover {
          background: rgba(102, 126, 234, 0.1);
        }

        .url-history {
          margin-top: 15px;
          background: #f9f9f9;
          border-radius: 12px;
          padding: 15px;
          border: 1px solid #e0e0e0;
        }

        .history-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 10px;
          padding-bottom: 10px;
          border-bottom: 1px solid #e0e0e0;
          font-weight: 600;
          color: #666;
        }

        .history-list {
          list-style: none;
          padding: 0;
          margin: 0;
          max-height: 200px;
          overflow-y: auto;
        }

        .history-item {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 10px;
          cursor: pointer;
          border-radius: 8px;
          transition: all 0.3s ease;
          color: #333;
        }

        .history-item:hover {
          background: #e8e8ff;
        }

        .history-icon {
          font-size: 18px;
          min-width: 24px;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .history-url {
          font-size: 13px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        @media (max-width: 768px) {
          .input-group {
            flex-direction: column;
          }
          
          .submit-btn {
            width: 100%;
            justify-content: center;
            padding: 15px;
          }
        }
      `}</style>
    </form>
  );
}

export default DownloadForm;