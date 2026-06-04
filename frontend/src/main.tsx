import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';

import { App } from './App';
import './index.css';
import { ThemeProvider } from './theme/ThemeProvider';

const proxyMatch = window.location.pathname.match(/^(\/api\/preview\/proxy\/[a-f0-9]+)/);
const basename = proxyMatch ? proxyMatch[1] : undefined;

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <BrowserRouter basename={basename}>
      <ThemeProvider>
        <App />
      </ThemeProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
