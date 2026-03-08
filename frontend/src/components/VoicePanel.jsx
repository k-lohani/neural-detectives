import React, { useState } from 'react';
import '../index.css';

const VoicePanel = ({ detectiveMessage, isRecording, isSpeaking, toggleRecording, sendTranscript, requestHint, hintCount = 0 }) => {
    const [textInput, setTextInput] = useState("");

    const handleSend = () => {
        if (textInput.trim() && sendTranscript) {
            sendTranscript(textInput);
            setTextInput("");
        }
    };

    const ringState = isRecording ? 'listening' : isSpeaking ? 'speaking' : '';

    return (
        <div className="voice-panel glass-panel">
            <div className={`detective-avatar-wrapper ${ringState}`}>
                <div className="avatar-ring" />
                <div className="detective-avatar">
                    <img
                        src="/detective.png"
                        alt="Detective Louis"
                        className="detective-avatar-img"
                        onError={(e) => { e.target.style.display='none'; }}
                    />
                </div>
            </div>
            <span className="detective-label">Detective Louis</span>

            <div className="voice-status">
                <p className="status-text">{detectiveMessage || "Waiting for your lead, partner..."}</p>
                <div className={`waveform ${isRecording ? 'active' : ''}`}>
                    <div className="bar" /><div className="bar" /><div className="bar" /><div className="bar" /><div className="bar" />
                </div>
            </div>

            <div className="voice-controls">
                <button
                    className={`mic-button ${isRecording ? 'recording' : ''}`}
                    onClick={toggleRecording}
                >
                    <span className="btn-icon">{isRecording ? '\u25A0' : '\u25CF'}</span>
                    {isRecording ? 'Listening...' : 'Speak'}
                </button>
                <button className="hint-button" onClick={requestHint} title={`Hints used: ${hintCount} (-10 pts each)`}>
                    <span className="btn-icon">?</span>
                    Hint{hintCount > 0 ? ` (${hintCount})` : ''}
                </button>
            </div>

            <div className="text-input-row">
                <input
                    type="text"
                    value={textInput}
                    onChange={e => setTextInput(e.target.value)}
                    placeholder="Type your question..."
                    onKeyDown={e => e.key === 'Enter' && handleSend()}
                    className="detective-input"
                />
                <button onClick={handleSend} className="send-button" disabled={!textInput.trim()}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
                </button>
            </div>
        </div>
    );
};

export default VoicePanel;
