import React from 'react';
import {createRoot} from 'react-dom/client';
import App from './AppNovo.jsx';
import 'leaflet/dist/leaflet.css';
import './style.css';
import './refinement.css';
createRoot(document.getElementById('root')).render(<App/>);
