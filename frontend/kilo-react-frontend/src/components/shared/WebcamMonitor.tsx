import React, { useEffect, useRef, useState } from 'react';

interface WebcamMonitorProps {
  apiBaseUrl?: string;
  floating?: boolean;
  widthClass?: string;
  heightClass?: string;
  className?: string;
  compact?: boolean; // render compact inline preview
  onClick?: () => void; // click handler (used by Admin compact preview)
}

export const WebcamMonitor = ({ apiBaseUrl = process.env.REACT_APP_API_BASE_URL || '/api', floating = true, widthClass = 'w-64', heightClass = 'h-48', className = '', compact = false, onClick }: WebcamMonitorProps): import('react').JSX.Element => {
  const [isWatching, setIsWatching] = useState(false);
  const [lastDetection, setLastDetection] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [isMinimized, setIsMinimized] = useState(false);
  const [hasFrame, setHasFrame] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // Use API base URL (proxied through nginx to gateway, which routes to cam service)
  const camServiceUrl = `${apiBaseUrl}/cam`;

  const checkCamService = React.useCallback(async () => {
    try {
      const response = await fetch(`${camServiceUrl}/status`);
      if (response.ok) {
        setIsWatching(true);
        setError('');
      } else {
        setError('Cam service offline');
      }
    } catch (err) {
      setError('Server camera unavailable');
      console.error('Cam service check failed:', err);
    }
  }, [camServiceUrl]);

  const startMonitoring = React.useCallback(() => {
    // Poll for webcam frames every 500ms
    intervalRef.current = setInterval(async () => {
      try {
        const response = await fetch(`${camServiceUrl}/stream`, {
          method: 'GET',
          cache: 'no-cache',
        });

        if (response.ok) {
          const blob = await response.blob();

          // Check if blob is actually an image
          if (blob.type.startsWith('image/')) {
            const imageUrl = URL.createObjectURL(blob);

            if (imgRef.current) {
              // Revoke old URL to prevent memory leak
              if (imgRef.current.src && imgRef.current.src.startsWith('blob:')) {
                URL.revokeObjectURL(imgRef.current.src);
              }
              imgRef.current.src = imageUrl;
              setHasFrame(true);
            }

            setIsWatching(true);
            setLastDetection(new Date().toLocaleTimeString());
            setError('');
          } else {
            console.error('Received non-image blob:', blob.type);
            setError('Invalid stream format');
          }
        } else {
          console.error('Stream request failed:', response.status);
          setError(`Stream error: ${response.status}`);
        }
      } catch (err) {
        console.error('Stream fetch error:', err);
        setError('Connection failed');
      }
    }, 500);
  }, [camServiceUrl]);

  const stopMonitoring = React.useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setHasFrame(false);
  }, []);

  useEffect(() => {
    // Check if cam service is available
    checkCamService();

    // Start streaming frames from webcam
    startMonitoring();

    return () => {
      stopMonitoring();
    };
  }, [checkCamService, startMonitoring, stopMonitoring]);

  const containerPositionClass = floating ? 'fixed bottom-6 right-6 z-50' : 'relative';

  return (
    <div className={`${containerPositionClass} ${className}`}>
      <div className="bg-dark-card border-2 border-zombie-green rounded-xl shadow-lg overflow-hidden">
        {/* Header (hidden in compact mode) */}
        {!compact && (
          <div className="bg-dark-bg border-b-2 border-zombie-green px-4 py-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className={`w-3 h-3 rounded-full ${isWatching ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
                <span className="text-sm font-bold text-zombie-green terminal-glow">
                  {isWatching ? 'SYSTEM MONITORING' : 'OFFLINE'}
                </span>
              </div>
              <div className="flex items-center gap-2">
                {lastDetection && !isMinimized && (
                  <span className="text-xs text-zombie-green opacity-70">{lastDetection}</span>
                )}
                <button
                  onClick={() => setIsMinimized(!isMinimized)}
                  className="text-zombie-green hover:text-terminal-green text-lg font-bold leading-none"
                  title={isMinimized ? "Expand" : "Minimize"}
                >
                  {isMinimized ? '□' : '_'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Video Feed */}
        {!isMinimized && (
          <div
            onClick={compact && onClick ? onClick : undefined}
            className={`${widthClass} ${heightClass} bg-dark-bg relative ${compact ? 'cursor-pointer' : ''}`}
          > 
            {error ? (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-center p-4">
                  <p className="text-zombie-green text-sm mb-2">⚠️</p>
                  <p className="text-zombie-green text-xs">{error}</p>
                  <button
                    onClick={checkCamService}
                    className="mt-2 px-3 py-1 bg-zombie-green text-dark-bg text-xs rounded hover:bg-terminal-green"
                  >
                    RETRY
                  </button>
                </div>
              </div>
            ) : (
              <>
                <img
                  ref={imgRef}
                  alt="Webcam monitoring feed"
                  data-has-frame={hasFrame ? 'true' : undefined}
                  className="w-full h-full object-cover"
                />
                {isWatching && (
                  <div className="absolute top-2 left-2 bg-zombie-green text-dark-bg text-xs font-bold px-2 py-1 rounded">
                    LIVE
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* Footer (hidden in compact mode) */}
        {!compact && !isMinimized && (
          <div className="bg-dark-bg border-t-2 border-zombie-green px-4 py-2">
            <p className="text-xs text-zombie-green text-center">
              📹 PC Webcam Active
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
