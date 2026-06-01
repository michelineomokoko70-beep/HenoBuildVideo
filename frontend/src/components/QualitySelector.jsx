import React from 'react';

function QualitySelector({ formats, onSelect, selected }) {
  return (
    <div className="quality-selector">
      <h4>Sélectionnez la qualité:</h4>
      <div className="quality-options">
        {formats.map((format) => (
          <button
            key={format.format_id}
            className={`quality-btn ${selected?.format_id === format.format_id ? 'selected' : ''}`}
            onClick={() => onSelect(format)}
          >
            {format.quality || format.resolution}
            <span className="format-ext">.{format.ext}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

export default QualitySelector;