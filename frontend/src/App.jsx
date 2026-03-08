import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import CasePage from './pages/CasePage';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/case" element={<CasePage />} />
      </Routes>
    </Router>
  );
}

export default App;
