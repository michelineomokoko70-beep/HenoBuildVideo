import React from 'react';

function ProgressBar({ progress, status }) {
  const getStatusText = () => {
    if (status === 'starting') return 'Initialisation du téléchargement...';
    if (status === 'processing') return 'Fusion de l\'audio et de la vidéo en cours (FFmpeg)...';
    if (status === 'completed') return 'Téléchargement terminé !';
    return 'Téléchargement de la vidéo en cours...';
  };

  return (
    <div className="progress-container">
      <div className="progress-status-text">{getStatusText()}</div>
      <div className="progress-bar">
        <div 
          className={`progress-fill ${status === 'processing' ? 'processing-pulse' : ''}`} 
          style={{ width: `${progress}%` }}
        />
      </div>
      <p className="progress-text">{Math.round(progress)}%</p>
    </div>
  );
}

export default ProgressBar;