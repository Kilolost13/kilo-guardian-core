/**
 * Device Detection Utility
 * Detects whether the app is running on a server/desktop or tablet device
 */

import { useState, useEffect } from 'react';

export type DeviceType = 'server' | 'tablet';

export interface DeviceInfo {
  type: DeviceType;
  isTouch: boolean;
  screenWidth: number;
  screenHeight: number;
  userAgent: string;
}

/**
 * Detect current device type based on screen size and user agent
 */
export function detectDevice(): DeviceInfo {
  const width = window.innerWidth;
  const height = window.innerHeight;
  const ua = navigator.userAgent.toLowerCase();

  // Check if device has touch support
  const isTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;

  // Tablet detection logic:
  // 1. Touch-enabled device
  // 2. Screen width between 600-1400px (typical tablet range)
  // 3. OR user agent contains tablet/mobile keywords
  const isTabletUA = /tablet|ipad|playbook|silk|android(?!.*mobile)/i.test(ua) ||
                     (/android/i.test(ua) && !/mobile/i.test(ua));

  const isTabletSize = width >= 600 && width <= 1400 && isTouch;

  const isTablet = isTabletUA || isTabletSize;

  return {
    type: isTablet ? 'tablet' : 'server',
    isTouch,
    screenWidth: width,
    screenHeight: height,
    userAgent: ua
  };
}

/**
 * Get features available for current device
 */
export function getDeviceFeatures(device: DeviceInfo) {
  if (device.type === 'tablet') {
    return {
      showServerCamera: false,      // Hide server camera on tablet
      showTabletCamera: true,        // Show tablet camera
      showFullAdminPanel: false,     // Simplified admin on tablet
      showVoiceInput: true,         // Voice available on both
      showTouchOptimization: true,  // Optimize for touch
      showAdvancedFeatures: false   // Hide complex features
    };
  } else {
    return {
      showServerCamera: true,       // Show server camera
      showTabletCamera: false,      // Hide tablet camera
      showFullAdminPanel: true,     // Full admin panel
      showVoiceInput: true,        // Voice available on both
      showTouchOptimization: false, // Standard desktop UI
      showAdvancedFeatures: true   // Show all features
    };
  }
}

/**
 * React hook for device detection
 */
export function useDeviceDetection() {
  const [deviceInfo, setDeviceInfo] = useState<DeviceInfo>(detectDevice());
  const [features, setFeatures] = useState(getDeviceFeatures(deviceInfo));

  useEffect(() => {
    const handleResize = () => {
      const newDeviceInfo = detectDevice();
      setDeviceInfo(newDeviceInfo);
      setFeatures(getDeviceFeatures(newDeviceInfo));
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return { deviceInfo, features };
}
