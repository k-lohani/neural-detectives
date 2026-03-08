import React, { useState, useEffect } from 'react';
import '../index.css';

const CenterPedestal = ({ suspects = [], focusEntity }) => {
    const [activeIndex, setActiveIndex] = useState(0);

    useEffect(() => {
        if (!focusEntity || !suspects.length) return;
        const idx = suspects.findIndex(s =>
            s.name.toLowerCase().includes(focusEntity.toLowerCase()) ||
            focusEntity.toLowerCase().includes(s.name.toLowerCase())
        );
        if (idx !== -1 && idx !== activeIndex) {
            setActiveIndex(idx);
        }
    }, [focusEntity, suspects]);

    if (!suspects.length) return null;

    const nextSuspect = () => setActiveIndex((i) => (i + 1) % suspects.length);
    const prevSuspect = () => setActiveIndex((i) => (i - 1 + suspects.length) % suspects.length);

    return (
        <div className="pedestal-container">
            <div className="spotlight" />

            <div className="carousel">
                <button className="carousel-nav prev" onClick={prevSuspect} aria-label="Previous suspect">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
                </button>

                <div className="suspect-stage">
                    {suspects.map((suspect, index) => {
                        let position = "hidden";
                        if (index === activeIndex) position = "active";
                        else if (index === (activeIndex - 1 + suspects.length) % suspects.length) position = "prev";
                        else if (index === (activeIndex + 1) % suspects.length) position = "next";

                        return (
                            <div key={suspect.id || index} className={`suspect-card ${position}`}>
                                <div className="suspect-image-wrapper">
                                    {suspect.icon ? (
                                        <img src={`data:image/png;base64,${suspect.icon}`} alt={suspect.name} className="suspect-icon-img" />
                                    ) : (
                                        <div className="suspect-fallback">
                                            <span>{suspect.name?.charAt(0) || '?'}</span>
                                        </div>
                                    )}
                                </div>
                                <div className="suspect-info">
                                    <h2 className="suspect-name">{suspect.name}</h2>
                                    <div className="suspect-traits">
                                        {suspect.traits?.map((trait, idx) => (
                                            <span key={idx} className="trait-tag">{trait}</span>
                                        ))}
                                    </div>
                                    <p className="suspect-description">{suspect.description}</p>
                                </div>
                            </div>
                        );
                    })}
                </div>

                <button className="carousel-nav next" onClick={nextSuspect} aria-label="Next suspect">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
                </button>
            </div>

            <div className="suspect-counter">
                {suspects.map((_, i) => (
                    <span key={i} className={`counter-dot ${i === activeIndex ? 'active' : ''}`} onClick={() => setActiveIndex(i)} />
                ))}
            </div>

            <div className="pedestal-base" />
        </div>
    );
};

export default CenterPedestal;
