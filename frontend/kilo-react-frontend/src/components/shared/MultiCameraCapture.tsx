import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Button } from './Button';

interface CameraDevice {
  deviceId: string;
  label: string;
  facing?: 'user' | 'environment' | 'unknown';
}

interface CameraStream {
  deviceId: string;
  stream: MediaStream | null;
  videoRef: React.RefObject<HTMLVideoElement>;
  error: string | null;
  isActive: boolean;
}

interface CapturedImage {
  deviceId: string;
  label: string;
  dataUrl: string;
  timestamp: number;
}

interface MultiCameraCaptureProps {
  onCapture: (images: CapturedImage[]) => void;
  onClose: () => void;
  maxCameras?: number;
}

export const MultiCameraCapture: React.FC<MultiCameraCaptureProps> = ({
  onCapture,
  onClose,
  maxCameras = 4,
}) => {
  const [cameras, setCameras] = useState<CameraDevice[]>([]);
  const [selectedCameras, setSelectedCameras] = useState<Set<string>>(new Set());
  const [cameraStreams, setCameraStreams] = useState<Map<string, CameraStream>>(new Map());
  const [isScanning, setIsScanning] = useState(false);
  const [isCapturing, setIsCapturing] = useState(false);
  const [capturedImages, setCapturedImages] = useState<CapturedImage[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Enumerate all available cameras
  const enumerateCameras = useCallback(async () => {
    try {
      setIsScanning(true);
      setError(null);

      // Request permission first to get device labels
      const tempStream = await navigator.mediaDevices.getUserMedia({ video: true });
      tempStream.getTracks().forEach(track => track.stop());

      // Now enumerate with labels
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = devices.filter(device => device.kind === 'videoinput');

      const cameraList: CameraDevice[] = videoDevices.map((device, index) => {
        let facing: 'user' | 'environment' | 'unknown' = 'unknown';
        const label = device.label.toLowerCase();

        if (label.includes('front') || label.includes('user')) {
          facing = 'user';
        } else if (label.includes('back') || label.includes('rear') || label.includes('environment')) {
          facing = 'environment';
        }

        return {
          deviceId: device.deviceId,
          label: device.label || `Camera ${index + 1}`,
          facing,
        };
      });

      setCameras(cameraList);

      if (cameraList.length === 0) {
        setError('No cameras found. Please connect a camera and try again.');
      }
    } catch (err) {
      console.error('Error enumerating cameras:', err);
      setError('Failed to access cameras. Please grant camera permissions.');
    } finally {
      setIsScanning(false);
    }
  }, []);

  // Toggle camera selection
  const toggleCameraSelection = (deviceId: string) => {
    setSelectedCameras(prev => {
      const newSet = new Set(prev);
      if (newSet.has(deviceId)) {
        newSet.delete(deviceId);
        // Stop stream if deselected
        stopCameraStream(deviceId);
      } else {
        if (newSet.size < maxCameras) {
          newSet.add(deviceId);
        }
      }
      return newSet;
    });
  };

  // Start stream for a specific camera
  const startCameraStream = async (deviceId: string) => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          deviceId: { exact: deviceId },
          width: { ideal: 1920 },
          height: { ideal: 1080 },
        },
      });

      const videoRef = React.createRef<HTMLVideoElement>();

      setCameraStreams(prev => {
        const newMap = new Map(prev);
        newMap.set(deviceId, {
          deviceId,
          stream,
          videoRef,
          error: null,
          isActive: true,
        });
        return newMap;
      });

      return videoRef;
    } catch (err) {
      console.error(`Error starting camera ${deviceId}:`, err);
      setCameraStreams(prev => {
        const newMap = new Map(prev);
        newMap.set(deviceId, {
          deviceId,
          stream: null,
          videoRef: React.createRef<HTMLVideoElement>(),
          error: 'Failed to start camera',
          isActive: false,
        });
        return newMap;
      });
      return null;
    }
  };

  // Stop stream for a specific camera
  const stopCameraStream = (deviceId: string) => {
    const cameraStream = cameraStreams.get(deviceId);
    if (cameraStream?.stream) {
      cameraStream.stream.getTracks().forEach(track => track.stop());
      setCameraStreams(prev => {
        const newMap = new Map(prev);
        newMap.delete(deviceId);
        return newMap;
      });
    }
  };

  // Start all selected camera streams
  const startAllStreams = async () => {
    for (const deviceId of Array.from(selectedCameras)) {
      await startCameraStream(deviceId);
    }
  };

  // Stop all camera streams
  const stopAllStreams = () => {
    Array.from(cameraStreams.keys()).forEach((deviceId) => {
      stopCameraStream(deviceId);
    });
  };

  // Capture from a single camera
  const captureFromCamera = (deviceId: string, stream: CameraStream): CapturedImage | null => {
    if (!stream.videoRef.current || !stream.stream) {
      return null;
    }

    const video = stream.videoRef.current;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext('2d');
    if (!ctx) return null;

    ctx.drawImage(video, 0, 0);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.95);

    const camera = cameras.find(c => c.deviceId === deviceId);

    return {
      deviceId,
      label: camera?.label || 'Unknown Camera',
      dataUrl,
      timestamp: Date.now(),
    };
  };

  // Capture from all active cameras simultaneously
  const captureAll = async () => {
    if (cameraStreams.size === 0) {
      setError('No active camera streams. Please select cameras first.');
      return;
    }

    try {
      setIsCapturing(true);
      const images: CapturedImage[] = [];

      // Capture from all cameras simultaneously
      Array.from(cameraStreams.entries()).forEach(([deviceId, stream]) => {
        const image = captureFromCamera(deviceId, stream);
        if (image) {
          images.push(image);
        }
      });

      if (images.length === 0) {
        setError('Failed to capture images from any camera.');
        return;
      }

      setCapturedImages(images);

      // Call parent callback with all captured images
      onCapture(images);
    } catch (err) {
      console.error('Error capturing images:', err);
      setError('Failed to capture images. Please try again.');
    } finally {
      setIsCapturing(false);
    }
  };

  // Initialize: enumerate cameras on mount
  useEffect(() => {
    enumerateCameras();

    // Cleanup: stop all streams on unmount
    return () => {
      stopAllStreams();
    };
  }, [enumerateCameras]);

  // Start/stop streams when selection changes
  useEffect(() => {
    // Start streams for newly selected cameras
    Array.from(selectedCameras).forEach(deviceId => {
      if (!cameraStreams.has(deviceId)) {
        startCameraStream(deviceId);
      }
    });

    // Stop streams for deselected cameras
    Array.from(cameraStreams.entries()).forEach(([deviceId, stream]) => {
      if (!selectedCameras.has(deviceId)) {
        stopCameraStream(deviceId);
      }
    });
  }, [selectedCameras]);

  // Attach streams to video elements
  useEffect(() => {
    Array.from(cameraStreams.entries()).forEach(([deviceId, stream]) => {
      if (stream.videoRef.current && stream.stream) {
        stream.videoRef.current.srcObject = stream.stream;
      }
    });
  }, [cameraStreams]);

  const getCameraIcon = (facing?: 'user' | 'environment' | 'unknown') => {
    switch (facing) {
      case 'user':
        return '🤳';
      case 'environment':
        return '📷';
      default:
        return '🎥';
    }
  };

  return (
    <div className="fixed inset-0 bg-black/90 z-50 flex flex-col p-4">
      {/* Header */}
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold text-zombie-green terminal-glow">
          Multi-Camera Capture
        </h2>
        <Button variant="danger" onClick={onClose} size="sm">
          Close
        </Button>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-900/20 border-2 border-red-600 rounded-lg p-3 mb-4">
          <p className="text-red-400 flex items-center gap-2">
            <span className="text-xl">✗</span> {error}
          </p>
        </div>
      )}

      {/* Camera Selection List */}
      <div className="bg-dark-card border-2 border-dark-border rounded-lg p-4 mb-4">
        <div className="flex justify-between items-center mb-3">
          <h3 className="text-lg font-semibold text-zombie-green">
            Available Cameras ({cameras.length})
          </h3>
          <Button variant="secondary" onClick={enumerateCameras} size="sm" disabled={isScanning}>
            <span className={isScanning ? 'inline-block animate-spin' : ''}>⟳</span>
            {isScanning ? 'Scanning...' : 'Refresh'}
          </Button>
        </div>

        {cameras.length === 0 ? (
          <p className="text-gray-400 text-center py-4">
            {isScanning ? 'Scanning for cameras...' : 'No cameras found'}
          </p>
        ) : (
          <div className="space-y-2">
            {cameras.map((camera) => (
              <button
                key={camera.deviceId}
                onClick={() => toggleCameraSelection(camera.deviceId)}
                disabled={!selectedCameras.has(camera.deviceId) && selectedCameras.size >= maxCameras}
                className={`w-full p-3 rounded-lg border-2 transition-all flex items-center gap-3 ${
                  selectedCameras.has(camera.deviceId)
                    ? 'bg-zombie-green/10 border-zombie-green'
                    : 'bg-dark-bg border-dark-border hover:border-zombie-green/50'
                } ${
                  !selectedCameras.has(camera.deviceId) && selectedCameras.size >= maxCameras
                    ? 'opacity-50 cursor-not-allowed'
                    : 'cursor-pointer'
                }`}
              >
                <span className="text-2xl">{getCameraIcon(camera.facing)}</span>
                <div className="flex-1 text-left">
                  <p className="text-white font-medium">{camera.label}</p>
                  <p className="text-gray-400 text-sm">
                    {camera.facing === 'user' ? 'Front' : camera.facing === 'environment' ? 'Back' : 'External'}
                  </p>
                </div>
                {selectedCameras.has(camera.deviceId) && (
                  <span className="text-zombie-green text-2xl">✓</span>
                )}
              </button>
            ))}
          </div>
        )}

        <p className="text-gray-400 text-sm mt-3 text-center">
          Selected: {selectedCameras.size} / {maxCameras}
        </p>
      </div>

      {/* Live Preview Grid */}
      {cameraStreams.size > 0 && (
        <div className="flex-1 bg-dark-card border-2 border-dark-border rounded-lg p-4 overflow-auto mb-4">
          <h3 className="text-lg font-semibold text-zombie-green mb-3">
            Live Preview ({cameraStreams.size} cameras)
          </h3>

          <div className={`grid gap-4 ${
            cameraStreams.size === 1 ? 'grid-cols-1' :
            cameraStreams.size === 2 ? 'grid-cols-2' :
            'grid-cols-2 lg:grid-cols-2'
          }`}>
            {Array.from(cameraStreams.entries()).map(([deviceId, stream]) => {
              const camera = cameras.find(c => c.deviceId === deviceId);
              return (
                <div key={deviceId} className="bg-dark-bg rounded-lg overflow-hidden border-2 border-zombie-green/30">
                  <div className="bg-dark-border p-2 flex items-center gap-2">
                    <span className="text-xl">{getCameraIcon(camera?.facing)}</span>
                    <p className="text-white font-medium text-sm">{camera?.label}</p>
                  </div>

                  {stream.error ? (
                    <div className="aspect-video flex items-center justify-center bg-red-900/20">
                      <p className="text-red-400">{stream.error}</p>
                    </div>
                  ) : (
                    <video
                      ref={stream.videoRef}
                      autoPlay
                      playsInline
                      muted
                      className="w-full aspect-video object-cover"
                    />
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Captured Images Preview */}
      {capturedImages.length > 0 && (
        <div className="bg-dark-card border-2 border-zombie-green rounded-lg p-4 mb-4">
          <h3 className="text-lg font-semibold text-zombie-green mb-3">
            Captured Images ({capturedImages.length})
          </h3>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
            {capturedImages.map((image) => (
              <div key={image.deviceId} className="relative">
                <img
                  src={image.dataUrl}
                  alt={image.label}
                  className="w-full aspect-video object-cover rounded border-2 border-zombie-green/50"
                />
                <p className="text-xs text-gray-400 mt-1 truncate">{image.label}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-3">
        <Button
          variant="primary"
          onClick={captureAll}
          disabled={cameraStreams.size === 0 || isCapturing}
          className="flex-1"
          size="lg"
        >
          <span className={isCapturing ? 'inline-block animate-pulse' : ''}>📷</span>
          {isCapturing ? 'Capturing...' : `Capture All (${cameraStreams.size})`}
        </Button>

        <Button
          variant="secondary"
          onClick={onClose}
          className="flex-1"
          size="lg"
        >
          Cancel
        </Button>
      </div>

      {/* Info */}
      <div className="mt-4 text-center">
        <p className="text-gray-400 text-sm">
          💡 Tip: Capture from multiple angles for better OCR accuracy
        </p>
      </div>
    </div>
  );
};
