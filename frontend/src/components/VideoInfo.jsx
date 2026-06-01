import React from 'react';

function VideoInfo({ info }) {
  return (
    <div className="video-info">
      <img 
        src={info.thumbnail} 
        alt={info.title}
        className="thumbnail"
      />
      
      <div className="video-details">
        <h3>{info.title}</h3>
        <p className="uploader">Par: {info.uploader}</p>
        <p className="duration">
          Durée: {Math.floor(info.duration / 60)}:{(info.duration % 60).toString().padStart(2, '0')}
        </p>
        <p className="platform">
          Plateforme: {info.platform === 'youtube' ? 'YouTube' : 'TikTok'}
        </p>
      </div>
    </div>
  );
}

export default VideoInfo;