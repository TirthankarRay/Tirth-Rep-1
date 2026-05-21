import { createBrowserRouter, Navigate } from 'react-router-dom';
import { App } from './App';
import { Queue } from './pages/Queue';
import { Proposal } from './pages/Proposal';
import { Audit } from './pages/Audit';
import { Settings } from './pages/Settings';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <Navigate to="/queue" replace /> },
      { path: 'queue', element: <Queue /> },
      { path: 'proposal/:id', element: <Proposal /> },
      { path: 'audit', element: <Audit /> },
      { path: 'settings', element: <Settings /> },
    ],
  },
]);
