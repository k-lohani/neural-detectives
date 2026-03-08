import React from 'react';
import { useNavigate } from 'react-router-dom';

const EndGameOverlay = ({ caseData, score, solution, elapsedSeconds, hintCount, incorrectAccusations }) => {
    const navigate = useNavigate();

    const formatTime = (s) => {
        const m = Math.floor(s / 60);
        const sec = s % 60;
        return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
    };

    const solWho = solution?.who?.name || 'Unknown';
    const solWhat = solution?.what?.name || 'Unknown';
    const solWhere = solution?.where?.name || 'Unknown';

    const scoreVal = score ?? 0;
    const rating = scoreVal >= 80 ? 'Master Detective' : scoreVal >= 50 ? 'Sharp Eye' : 'Rookie';

    return (
        <div className="endgame-overlay">
            <div className="endgame-content glass-panel">
                <div className="endgame-badge">CASE CLOSED</div>
                <h1 className="endgame-title">{caseData?.title || 'The Mystery'}</h1>

                <div className="endgame-divider" />

                <div className="endgame-solution">
                    <div className="solution-row">
                        <span className="solution-label">Murderer</span>
                        <span className="solution-value">{solWho}</span>
                    </div>
                    <div className="solution-row">
                        <span className="solution-label">Weapon</span>
                        <span className="solution-value">{solWhat}</span>
                    </div>
                    <div className="solution-row">
                        <span className="solution-label">Location</span>
                        <span className="solution-value">{solWhere}</span>
                    </div>
                </div>

                <div className="endgame-score-section">
                    <div className="score-circle">
                        <span className="score-number">{scoreVal}</span>
                    </div>
                    <span className="score-out-of">/ 100</span>
                </div>
                <p className="score-rating">{rating}</p>

                <div className="endgame-stats">
                    <div className="stat">
                        <span className="stat-value">{formatTime(elapsedSeconds)}</span>
                        <span className="stat-label">Time</span>
                    </div>
                    <div className="stat-divider" />
                    <div className="stat">
                        <span className="stat-value">{hintCount}</span>
                        <span className="stat-label">Hints Used</span>
                    </div>
                    <div className="stat-divider" />
                    <div className="stat">
                        <span className="stat-value">{incorrectAccusations}</span>
                        <span className="stat-label">Wrong Guesses</span>
                    </div>
                </div>

                <button className="start-button endgame-replay" onClick={() => navigate('/')}>
                    New Case
                </button>
            </div>
        </div>
    );
};

export default EndGameOverlay;
