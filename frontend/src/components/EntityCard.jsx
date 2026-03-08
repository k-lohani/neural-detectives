import React, { useState, useEffect } from 'react';

const EntityCard = ({ entity, focusEntity }) => {
    const [flipped, setFlipped] = useState(false);

    useEffect(() => {
        if (!focusEntity || !entity) return;
        const match =
            entity.name.toLowerCase().includes(focusEntity.toLowerCase()) ||
            focusEntity.toLowerCase().includes(entity.name.toLowerCase());
        if (match && !flipped) {
            setFlipped(true);
        }
    }, [focusEntity, entity]);

    if (!entity) return null;

    return (
        <div
            className={`entity-flip-card ${flipped ? 'flipped' : ''}`}
            onClick={() => setFlipped(f => !f)}
            title="Click to reveal details"
        >
            <div className="entity-flip-inner">
                <div className="entity-flip-front">
                    {entity.icon ? (
                        <img
                            src={`data:image/png;base64,${entity.icon}`}
                            alt={entity.name}
                            className="entity-icon"
                        />
                    ) : (
                        <div className="entity-icon-placeholder">
                            <span>{entity.name?.charAt(0) || '?'}</span>
                        </div>
                    )}
                    <div className="entity-front-text">
                        <span className="entity-name">{entity.name}</span>
                        <span className="entity-flip-hint">Click to reveal</span>
                    </div>
                </div>
                <div className="entity-flip-back">
                    <span className="entity-name-back">{entity.name}</span>
                    <p className="entity-detail">{entity.detail || entity.description}</p>
                </div>
            </div>
        </div>
    );
};

export default EntityCard;
