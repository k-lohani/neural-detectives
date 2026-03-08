import React, { useEffect, useState, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import VoicePanel from '../components/VoicePanel';
import LogicGrid from '../components/LogicGrid';
import CenterPedestal from '../components/CenterPedestal';
import ComicStrip from '../components/ComicStrip';
import EntityCard from '../components/EntityCard';
import EndGameOverlay from '../components/EndGameOverlay';
import { useGameEngine } from '../hooks/useGameEngine';
import '../index.css';

const formatTimer = (totalSeconds) => {
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
};

const CasePage = () => {
  const location = useLocation();
  const difficulty = location.state?.difficulty || 'Easy';

  const [showModal, setShowModal] = useState(false);
  const [accuseWho, setAccuseWho] = useState('');
  const [accuseWhat, setAccuseWhat] = useState('');
  const [accuseWhere, setAccuseWhere] = useState('');

  const {
    caseData, isLoading, error, gridState, detectiveMessage,
    isCaseSolved, isRecording, isSpeaking, generateNewCase,
    sendTranscript, submitFinalAccusation, toggleRecording,
    focusEntity, suggestedAccusation, hintCount, incorrectAccusations,
    score, solution, elapsedSeconds, comicPanels, comicLoading, requestHint,
  } = useGameEngine();

  const prevSuggestionRef = useRef(null);

  useEffect(() => {
    generateNewCase(difficulty).then(() => {
      setShowModal(true);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [difficulty]);

  useEffect(() => {
    if (!suggestedAccusation) return;
    const key = `${suggestedAccusation.who}|${suggestedAccusation.what}|${suggestedAccusation.where}`;
    if (prevSuggestionRef.current === key) return;
    prevSuggestionRef.current = key;

    if (caseData) {
      const whoMatch = caseData.suspects?.find(s =>
        s.name.toLowerCase() === suggestedAccusation.who.toLowerCase());
      const whatMatch = caseData.weapons?.find(w =>
        w.name.toLowerCase() === suggestedAccusation.what.toLowerCase());
      const whereMatch = caseData.locations?.find(l =>
        l.name.toLowerCase() === suggestedAccusation.where.toLowerCase());

      if (whoMatch) setAccuseWho(whoMatch.name);
      if (whatMatch) setAccuseWhat(whatMatch.name);
      if (whereMatch) setAccuseWhere(whereMatch.name);
    }
  }, [suggestedAccusation, caseData]);

  if (error) {
    return (
      <div className="case-layout">
        <div className="loading-screen">
          <p className="loading-error">Something went wrong: {error}</p>
        </div>
      </div>
    );
  }

  if (isLoading || !caseData) {
    return (
      <div className="case-layout">
        <div className="loading-screen">
          <div className="loading-avatar-ring">
            <img src="/detective.png" alt="Detective Louis" className="loading-avatar-img" />
          </div>
          <h2 className="loading-title">Detective Louis is building the case file</h2>
          <div className="loading-bar-track">
            <div className="loading-bar-fill" />
          </div>
          <p className="loading-sub">Generating suspects, evidence, and locations...</p>
        </div>
      </div>
    );
  }

  const panels = comicPanels || caseData.comic_panels;

  return (
    <div className="case-layout">
      {isCaseSolved && (
        <EndGameOverlay
          caseData={caseData}
          score={score}
          solution={solution}
          elapsedSeconds={elapsedSeconds}
          hintCount={hintCount}
          incorrectAccusations={incorrectAccusations}
        />
      )}

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content glass-panel" onClick={e => e.stopPropagation()}>
            <div className="modal-badge">NEW CASE</div>
            <h2 className="modal-title">{caseData.title || "The Mystery"}</h2>
            {panels && panels.length > 0 ? (
              <ComicStrip panels={panels} title={caseData.title} />
            ) : comicLoading ? (
              <div className="modal-loading">
                <div className="loading-bar-track small"><div className="loading-bar-fill" /></div>
                <p>Generating scene illustrations...</p>
              </div>
            ) : (
              <p className="modal-premise">{caseData.premise}</p>
            )}
            <button className="start-button" onClick={() => setShowModal(false)}>Begin Investigation</button>
          </div>
        </div>
      )}

      <header className="case-header">
        <div className="header-left">
          <span className="header-badge">{difficulty.toUpperCase()}</span>
        </div>
        <h1 className="header-title" onClick={() => setShowModal(true)} title="Click to read premise">
          {caseData.title || "The Mystery"}
        </h1>
        <div className="header-right">
          <div className="timer-chip">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            <span className="timer-display">{formatTimer(elapsedSeconds)}</span>
          </div>
        </div>
      </header>

      <div className="main-content">
        <aside className="left-panel">
          <VoicePanel
            detectiveMessage={detectiveMessage}
            isRecording={isRecording}
            isSpeaking={isSpeaking}
            toggleRecording={toggleRecording}
            sendTranscript={sendTranscript}
            requestHint={requestHint}
            hintCount={hintCount}
          />
          <div className="clues-panel glass-panel">
            <h3>Investigation Notes</h3>
            <ul className="clues-list">
              {caseData.clues?.map((clue, idx) => (
                <li key={idx}>
                  <span className="clue-number">{idx + 1}</span>
                  {clue}
                </li>
              ))}
            </ul>
          </div>
        </aside>

        <section className="center-panel">
          <CenterPedestal suspects={caseData.suspects} focusEntity={focusEntity} />
        </section>

        <aside className="right-panel">
          <div className="weapons-locations glass-panel">
            <div className="section">
              <h3>Weapons</h3>
              <div className="card-grid">
                {caseData.weapons?.map(w => (
                  <EntityCard key={w.id} entity={w} focusEntity={focusEntity} />
                ))}
              </div>
            </div>
            <div className="section-divider" />
            <div className="section">
              <h3>Locations</h3>
              <div className="card-grid">
                {caseData.locations?.map(l => (
                  <EntityCard key={l.id} entity={l} focusEntity={focusEntity} />
                ))}
              </div>
            </div>
          </div>
        </aside>
      </div>

      <footer className="bottom-panel glass-panel">
        <LogicGrid caseData={caseData} gridState={gridState} />

        <div className="final-accusation">
          <h3>Final Accusation</h3>
          <div className="accusation-inputs">
            <div className="select-wrapper">
              <label className="select-label">WHO</label>
              <select value={accuseWho} onChange={e => setAccuseWho(e.target.value)}>
                <option value="">Select Murderer</option>
                {caseData.suspects?.map(s => <option key={s.id} value={s.name}>{s.name}</option>)}
              </select>
            </div>
            <div className="select-wrapper">
              <label className="select-label">WHAT</label>
              <select value={accuseWhat} onChange={e => setAccuseWhat(e.target.value)}>
                <option value="">Select Weapon</option>
                {caseData.weapons?.map(w => <option key={w.id} value={w.name}>{w.name}</option>)}
              </select>
            </div>
            <div className="select-wrapper">
              <label className="select-label">WHERE</label>
              <select value={accuseWhere} onChange={e => setAccuseWhere(e.target.value)}>
                <option value="">Select Location</option>
                {caseData.locations?.map(l => <option key={l.id} value={l.name}>{l.name}</option>)}
              </select>
            </div>
          </div>
          <button
            className={`submit-accusation ${suggestedAccusation ? 'pulse-glow' : ''}`}
            onClick={() => {
              if (!accuseWho || !accuseWhat || !accuseWhere) {
                alert("Select all three fields!");
              } else {
                submitFinalAccusation(accuseWho, accuseWhat, accuseWhere);
              }
            }}
          >Submit Case</button>
        </div>
      </footer>
    </div>
  );
};

export default CasePage;
