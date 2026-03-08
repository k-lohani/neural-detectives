import React, { useState } from 'react';

const PANEL_LABELS = ['I', 'II', 'III', 'IV'];

const ComicStrip = ({ panels = [], title }) => {
  const [selected, setSelected] = useState(null);

  if (!panels || panels.length === 0) return null;

  return (
    <div className="comic-strip-wrapper">
      <div className="comic-strip">
        {panels.map((panel, idx) => (
          <div
            key={idx}
            className="comic-panel"
            onClick={() => setSelected(idx)}
            title="Click to enlarge"
          >
            {/* Scene image */}
            <img
              src={`data:image/png;base64,${panel.image}`}
              alt={`Scene ${idx + 1}`}
              className="comic-panel-img"
            />

            {/* Panel number badge */}
            <div className="panel-number">{PANEL_LABELS[idx] || idx + 1}</div>

            {/* Bottom caption strip */}
            {panel.caption && (
              <div className="comic-panel-caption">
                <span>{panel.caption}</span>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Lightbox */}
      {selected !== null && (
        <div className="comic-lightbox" onClick={() => setSelected(null)}>
          <div className="comic-lightbox-content" onClick={e => e.stopPropagation()}>
            <button className="lightbox-close" onClick={() => setSelected(null)}>✕</button>
            <div className="lightbox-nav">
              <button
                className="lightbox-arrow"
                onClick={() => setSelected(prev => Math.max(0, prev - 1))}
                disabled={selected === 0}
              >‹</button>

              <div className="lightbox-panel-wrap">
                <img
                  src={`data:image/png;base64,${panels[selected].image}`}
                  alt={`Scene ${selected + 1}`}
                  className="lightbox-img"
                />
                {panels[selected].caption && (
                  <div className="lightbox-caption">
                    <p>{panels[selected].caption}</p>
                  </div>
                )}
              </div>

              <button
                className="lightbox-arrow"
                onClick={() => setSelected(prev => Math.min(panels.length - 1, prev + 1))}
                disabled={selected === panels.length - 1}
              >›</button>
            </div>
            <p className="lightbox-label">Panel {selected + 1} of {panels.length}</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default ComicStrip;
