function getElectronAPI() {
  if (typeof window === 'undefined') {
    return null;
  }
  return window.electronAPI || null;
}

const call = async (method, ...args) => {
  const api = getElectronAPI();
  if (!api || typeof api[method] !== 'function') {
    return null;
  }
  return api[method](...args);
};

const electronBridge = {
  isElectron() {
    return getElectronAPI()?.isElectron === true;
  },

  platform() {
    return getElectronAPI()?.platform || null;
  },

  getVersion() {
    return call('getVersion');
  },

  getDeviceId() {
    return call('getDeviceId');
  }
};

export default electronBridge;
