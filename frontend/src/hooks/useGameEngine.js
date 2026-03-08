import { useState, useCallback, useRef, useEffect } from 'react';

export function useGameEngine() {
  const [caseData, setCaseData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const [gridState, setGridState] = useState({});
  const [detectiveMessage, setDetectiveMessage] = useState("Waiting for your lead, partner...");
  const [isCaseSolved, setIsCaseSolved] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);

  const [focusEntity, setFocusEntity] = useState(null);
  const [suggestedAccusation, setSuggestedAccusation] = useState(null);
  const [hintCount, setHintCount] = useState(0);
  const [incorrectAccusations, setIncorrectAccusations] = useState(0);
  const [score, setScore] = useState(null);
  const [solution, setSolution] = useState(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [comicPanels, setComicPanels] = useState(null);
  const [comicLoading, setComicLoading] = useState(false);

  const ws = useRef(null);
  const recognitionRef = useRef(null);
  const fetchingRef = useRef(false);
  const timerRef = useRef(null);
  const caseIdRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const intentionalCloseRef = useRef(false);

  useEffect(() => {
    if (caseData && !isCaseSolved) {
      timerRef.current = setInterval(() => {
        setElapsedSeconds(prev => prev + 1);
      }, 1000);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [caseData, isCaseSolved]);

  const fetchComicPanelsBackground = useCallback(async (caseId) => {
    setComicLoading(true);
    try {
      const res = await fetch(`http://localhost:8000/api/game/${caseId}/comic-panels`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        if (data.comic_panels && data.comic_panels.length > 0) {
          setComicPanels(data.comic_panels);
          setCaseData(prev => prev ? { ...prev, comic_panels: data.comic_panels } : prev);
        }
      }
    } catch (e) {
      console.error('[GameEngine] Comic panel background fetch failed:', e);
    } finally {
      setComicLoading(false);
    }
  }, []);

  const connectWebSocket = useCallback((caseId) => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }

    if (ws.current) {
      intentionalCloseRef.current = true;
      ws.current.close();
      ws.current = null;
    }

    const socket = new WebSocket(`ws://localhost:8000/ws/game/${caseId}`);
    ws.current = socket;
    intentionalCloseRef.current = false;

    socket.onopen = () => {
      console.log("[WS] Connected to Detective Louis for case", caseId);
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'game_update') {
          if (data.voice_response) {
            setDetectiveMessage(data.voice_response);
            if (data.audio_base64) {
              setIsSpeaking(true);
              const snd = new Audio("data:audio/wav;base64," + data.audio_base64);
              snd.onended = () => setIsSpeaking(false);
              snd.onerror = () => setIsSpeaking(false);
              snd.play().catch(() => setIsSpeaking(false));
            } else if ('speechSynthesis' in window) {
              window.speechSynthesis.cancel();
              setIsSpeaking(true);
              const utterance = new SpeechSynthesisUtterance(data.voice_response);
              utterance.pitch = 0.8;
              utterance.rate = 0.95;
              utterance.onend = () => setIsSpeaking(false);
              const voices = window.speechSynthesis.getVoices();
              const louisVoice = voices.find(v => (v.lang.includes('en-GB') || v.lang.includes('en-US')) && v.name.includes('Male'))
                || voices.find(v => v.lang.includes('en-GB'))
                || voices[0];
              if (louisVoice) utterance.voice = louisVoice;
              window.speechSynthesis.speak(utterance);
            }
          }
          if (data.grid_update) setGridState(data.grid_update);
          if (data.focus_entity) setFocusEntity(data.focus_entity);
          if (data.suggested_accusation) setSuggestedAccusation(data.suggested_accusation);
          if (data.hint_count !== undefined) setHintCount(data.hint_count);
          if (data.incorrect_accusations !== undefined) setIncorrectAccusations(data.incorrect_accusations);

          if (data.is_solved) {
            setIsCaseSolved(true);
            if (data.score !== undefined) setScore(data.score);
            if (data.solution) setSolution(data.solution);
          }
        } else if (data.error) {
          setError(data.error);
        }
      } catch (e) {
        console.error("Error parsing websocket message", e);
      }
    };

    socket.onclose = () => {
      if (intentionalCloseRef.current) return;
      if (caseIdRef.current !== caseId) return;

      console.log("[WS] Disconnected — will reconnect in 3s for case", caseId);
      reconnectTimerRef.current = setTimeout(() => {
        if (caseIdRef.current === caseId) {
          connectWebSocket(caseId);
        }
      }, 3000);
    };
  }, []);

  const generateNewCase = async (difficulty) => {
    if (fetchingRef.current) return null;
    fetchingRef.current = true;

    caseIdRef.current = null;
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (ws.current) {
      intentionalCloseRef.current = true;
      ws.current.close();
      ws.current = null;
    }

    setIsLoading(true);
    setError(null);
    setElapsedSeconds(0);
    setHintCount(0);
    setIncorrectAccusations(0);
    setScore(null);
    setSolution(null);
    setIsCaseSolved(false);
    setSuggestedAccusation(null);
    setFocusEntity(null);
    setComicPanels(null);
    setIsSpeaking(false);

    try {
      const response = await fetch(`http://localhost:8000/api/game/new?difficulty=${difficulty}`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error("Failed to generate case");
      const data = await response.json();

      setCaseData(data.case);
      caseIdRef.current = data.case_id;
      connectWebSocket(data.case_id);
      fetchComicPanelsBackground(data.case_id);

      return data.case;
    } catch (err) {
      setError(err.message);
      setIsLoading(false);
      return null;
    } finally {
      setIsLoading(false);
      fetchingRef.current = false;
    }
  };

  const sendTranscript = useCallback((transcript) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ transcript }));
      setDetectiveMessage("Detective Louis thinking...");
    }
  }, []);

  const submitFinalAccusation = useCallback((who, what, where) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({
        transcript: `I am ready to make my final accusation. ${who} did it with the ${what} in the ${where}.`
      }));
      setDetectiveMessage("Reviewing your accusation...");
    }
  }, []);

  const requestHint = useCallback(() => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ transcript: "Give me a hint, Louis." }));
      setDetectiveMessage("Detective Louis pondering a hint...");
    }
  }, []);

  if (!recognitionRef.current && ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognitionRef.current = new SpeechRecognition();
    recognitionRef.current.continuous = false;
    recognitionRef.current.interimResults = false;
    recognitionRef.current.lang = 'en-US';

    recognitionRef.current.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      console.log("Captured speech:", transcript);
      sendTranscript(transcript);
      setIsRecording(false);
    };

    recognitionRef.current.onerror = (event) => {
      console.error("Speech recognition error", event.error);
      setIsRecording(false);
    };

    recognitionRef.current.onend = () => {
      setIsRecording(false);
    };
  }

  const toggleRecording = () => {
    if (!recognitionRef.current) {
      alert("Speech Recognition API is not supported in this browser.");
      return;
    }

    if (isRecording) {
      recognitionRef.current.stop();
      setIsRecording(false);
    } else {
      try {
        recognitionRef.current.start();
        setIsRecording(true);
      } catch (e) {
        console.error("Could not start recording", e);
      }
    }
  };

  return {
    caseData,
    isLoading,
    error,
    gridState,
    detectiveMessage,
    isCaseSolved,
    isRecording,
    isSpeaking,
    generateNewCase,
    sendTranscript,
    submitFinalAccusation,
    toggleRecording,
    focusEntity,
    suggestedAccusation,
    hintCount,
    incorrectAccusations,
    score,
    solution,
    elapsedSeconds,
    comicPanels,
    comicLoading,
    requestHint,
  };
}
