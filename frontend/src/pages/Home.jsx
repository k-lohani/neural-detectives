import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import '../index.css';

const DIFFICULTIES = [
  { value: 'Easy', label: 'Easy', desc: '3 Suspects, Weapons & Locations', icon: 'I' },
  { value: 'Medium', label: 'Medium', desc: 'Statements & Hidden Lies', icon: 'II' },
  { value: 'Hard', label: 'Hard', desc: '4 Suspects, Weapons & Locations', icon: 'III' },
];

const Home = () => {
  const [difficulty, setDifficulty] = useState('Easy');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleStart = async () => {
    setIsLoading(true);
    setTimeout(() => {
      setIsLoading(false);
      navigate('/case', { state: { difficulty } });
    }, 1500);
  };

  return (
    <div className="home-container">
      <div className="home-bg-grain" />
      <div className="content-wrapper">
        <div className="home-avatar-ring">
          <img src="/detective.png" alt="Detective Louis" className="home-avatar-img" />
        </div>

        <h1 className="title">Noir Deductions</h1>
        <p className="subtitle">A murder mystery of logic and shadow</p>

        <div className="difficulty-cards">
          {DIFFICULTIES.map(d => (
            <button
              key={d.value}
              className={`diff-card ${difficulty === d.value ? 'diff-active' : ''}`}
              onClick={() => setDifficulty(d.value)}
              disabled={isLoading}
            >
              <span className="diff-icon">{d.icon}</span>
              <span className="diff-label">{d.label}</span>
              <span className="diff-desc">{d.desc}</span>
            </button>
          ))}
        </div>

        <button
          className="start-button"
          onClick={handleStart}
          disabled={isLoading}
        >
          {isLoading ? (
            <span className="loading-dots">Building case file<span className="dot-anim">...</span></span>
          ) : (
            'Start Investigation'
          )}
        </button>

        <p className="home-footer-text">Speak to Detective Louis. Deduce the truth. Solve the case.</p>
      </div>
    </div>
  );
};

export default Home;
