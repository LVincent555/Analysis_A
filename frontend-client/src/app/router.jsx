import React from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { DEFAULT_MODULE_ID, getModulePath, modules } from './moduleRegistry';

export default function AppRoutes({ appState }) {
  return (
    <Routes>
      {modules.map((module) => (
        <Route
          key={module.id}
          path={module.path === '/' ? '/' : module.path}
          element={module.render({ appState })}
        />
      ))}
      {modules.flatMap((module) => (module.aliases || []).map((alias) => (
        <Route
          key={`${module.id}:${alias}`}
          path={alias}
          element={<Navigate to={module.path} replace />}
        />
      )))}
      <Route path="*" element={<Navigate to={getModulePath(DEFAULT_MODULE_ID)} replace />} />
    </Routes>
  );
}
