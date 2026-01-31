import React, { useRef, useState, useEffect } from 'react';
import Webcam from 'react-webcam';
import { Button } from './Button';

interface CameraCaptureProps {
  onCapture: (imageBlob: Blob, imageDataUrl: string, allImages?: Blob[]) => void;
  onClose: () => void;
  type?: string; // 'prescription', 'receipt', 'general'
}

export const CameraCapture: React.FC<CameraCaptureProps> = ({
  onCapture,
  onClose,
  type = 'general'
}) => {
  const webcamRef = useRef<Webcam>(null);
  const [capturedImages, setCapturedImages] = useState<string[]>([]);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [focusTrigger, setFocusTrigger] = useState(0);

  const videoConstraints: MediaTrackConstraints = {
    width: { ideal: 1280 },
    height: { ideal: 720 },
    facingMode: 'environment', // Use back camera on mobile
    // @ts-ignore - focusMode is supported but not in TS types yet
    focusMode: 'continuous'
  };

  // Enable autofocus when camera is ready
  useEffect(() => {
    const enableAutofocus = async () => {
      const video = webcamRef.current?.video;
      if (video && video.srcObject) {
        const stream = video.srcObject as MediaStream;
        const videoTrack = stream.getVideoTracks()[0];

        if (videoTrack) {
          try {
            const capabilities = videoTrack.getCapabilities();
            console.log('Camera capabilities:', capabilities);

            // Try multiple autofocus strategies
            const constraints: any = {};

            // @ts-ignore - focusMode capability
            if (capabilities.focusMode) {
              // @ts-ignore
              if (capabilities.focusMode.includes('continuous')) {
                // @ts-ignore
                constraints.focusMode = 'continuous';
              // @ts-ignore
              } else if (capabilities.focusMode.includes('single-shot')) {
                // @ts-ignore
                constraints.focusMode = 'single-shot';
              }
            }

            // @ts-ignore - Try to set focus distance to auto (0 = infinity/auto)
            if (capabilities.focusDistance) {
              // @ts-ignore
              constraints.focusDistance = 0;
            }

            if (Object.keys(constraints).length > 0) {
              await videoTrack.applyConstraints(constraints);
              console.log('Applied focus constraints:', constraints);
            } else {
              console.log('No focus constraints available - camera may not support autofocus control');
            }
          } catch (error) {
            console.warn('Could not enable autofocus:', error);
          }
        }
      }
    };

    // Try to enable autofocus after a short delay to ensure camera is ready
    const timer = setTimeout(enableAutofocus, 1000);
    return () => clearTimeout(timer);
  }, [focusTrigger]);

  // Tap to refocus - triggers the useEffect again
  const handleTapToFocus = () => {
    setFocusTrigger(prev => prev + 1);
  };

  const capture = () => {
    const imageSrc = webcamRef.current?.getScreenshot();
    if (imageSrc) {
      setCapturedImages(prev => [...prev, imageSrc]);
    }
  };

  const removeImage = (index: number) => {
    setCapturedImages(prev => prev.filter((_, i) => i !== index));
  };

  const retake = () => {
    setCapturedImages([]);
  };

  const confirmCapture = async () => {
    if (capturedImages.length === 0) return;

    // Convert all captured images to blobs for stitching
    const allBlobs: Blob[] = [];
    for (const imgSrc of capturedImages) {
      const response = await fetch(imgSrc);
      const blob = await response.blob();
      allBlobs.push(blob);
    }

    // Send last image as primary, but include all for stitching
    const lastImgSrc = capturedImages[capturedImages.length - 1];
    const lastResponse = await fetch(lastImgSrc);
    const lastBlob = await lastResponse.blob();

    onCapture(lastBlob, lastImgSrc, allBlobs);
  };

  const handleUserMediaError = (error: any) => {
    console.error('Camera error:', error);
    setCameraError('Could not access camera. Please check permissions.');
  };

  return (
    <div className="fixed inset-0 bg-black z-50 flex flex-col">
      {/* Header - always visible at top */}
      <div className="flex justify-between items-center p-4 bg-gray-900 border-b border-gray-700">
        <h2 className="text-lg sm:text-xl font-bold text-white">
          📷 {type === 'prescription' ? 'SCAN PRESCRIPTION' :
              type === 'receipt' ? 'SCAN RECEIPT' : 'CAPTURE IMAGE'}
        </h2>
        <Button onClick={onClose} variant="secondary" size="sm">
          ✕
        </Button>
      </div>

      {/* Main content area - scrollable if needed */}
      <div className="flex-1 flex flex-col overflow-auto">
        {cameraError ? (
          <div className="flex-1 flex flex-col items-center justify-center p-4 text-center">
            <p className="text-red-500 text-xl mb-4">{cameraError}</p>
            <p className="text-gray-400 mb-4">To use the camera:</p>
            <ul className="text-left text-gray-300 space-y-2 mb-6">
              <li>• Allow camera permission in browser</li>
              <li>• Check device settings</li>
              <li>• Try using HTTPS instead of HTTP</li>
            </ul>
            <Button onClick={onClose} variant="primary" size="lg">
              OK
            </Button>
          </div>
        ) : capturedImages.length === 0 ? (
          <div className="flex-1 flex flex-col">
            {/* Camera preview - max 60vh height */}
            <div className="relative bg-black" style={{ maxHeight: '60vh' }} onClick={handleTapToFocus}>
              <Webcam
                ref={webcamRef}
                audio={false}
                screenshotFormat="image/jpeg"
                videoConstraints={videoConstraints}
                onUserMediaError={handleUserMediaError}
                className="w-full h-full object-cover"
              />

              {/* Camera overlay guide */}
              <div className="absolute inset-0 pointer-events-none">
                <div className="absolute inset-8 border-2 border-white border-dashed rounded-lg opacity-50"></div>
                <div className="absolute top-4 left-0 right-0 text-center">
                  <div className="inline-block bg-yellow-600 text-white px-3 py-2 rounded-lg text-xs font-bold">
                    📏 HOLD 12-18 INCHES FROM CAMERA
                  </div>
                </div>
                <div className="absolute bottom-4 left-0 right-0 text-center text-white text-xs sm:text-sm bg-black bg-opacity-50 py-2">
                  Position {type} within the frame • Good lighting needed
                </div>
              </div>
            </div>

            {/* Tip section - compact */}
            {type === 'prescription' && (
              <div className="bg-blue-900 bg-opacity-50 p-3 text-xs text-blue-200">
                <strong>📍 Tips for clear image:</strong><br/>
                • Hold bottle 12-18 inches from camera<br/>
                • Use good lighting (avoid shadows)<br/>
                • Keep camera steady<br/>
                • Rotate bottle to capture all text - take multiple photos
              </div>
            )}
            {type === 'receipt' && (
              <div className="bg-green-900 bg-opacity-50 p-3 text-xs text-green-200">
                <strong>📍 Tips for clear image:</strong><br/>
                • Hold receipt 12-18 inches from camera<br/>
                • Flatten receipt completely<br/>
                • Use good lighting (avoid shadows)<br/>
                • Keep camera steady when capturing
              </div>
            )}
          </div>
        ) : (
          <div className="flex-1 flex flex-col">
            {/* Live camera preview for additional captures - max 60vh height */}
            <div className="relative bg-black" style={{ maxHeight: '60vh' }} onClick={handleTapToFocus}>
              <Webcam
                ref={webcamRef}
                audio={false}
                screenshotFormat="image/jpeg"
                videoConstraints={videoConstraints}
                onUserMediaError={handleUserMediaError}
                className="w-full h-full object-cover"
              />
              <div className="absolute top-4 left-0 right-0 text-center">
                <div className="inline-block bg-green-600 text-white px-4 py-2 rounded-lg font-bold">
                  ✓ {capturedImages.length} PHOTO{capturedImages.length > 1 ? 'S' : ''} - TAP TO FOCUS
                </div>
              </div>
            </div>

            {/* Thumbnail strip at bottom */}
            <div className="bg-gray-900 p-2">
              <div className="flex gap-2 overflow-x-auto">
                {capturedImages.map((img, idx) => (
                  <div key={idx} className="relative flex-shrink-0" style={{ width: '80px', height: '80px' }}>
                    <img
                      src={img}
                      alt={`${idx + 1}`}
                      className="w-full h-full object-cover rounded border-2 border-green-500"
                    />
                    <button
                      onClick={() => removeImage(idx)}
                      className="absolute -top-1 -right-1 bg-red-600 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs font-bold"
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer buttons - always visible at bottom */}
      <div className="p-4 bg-gray-900 border-t border-gray-700">
        {capturedImages.length === 0 ? (
          <div className="flex gap-3">
            <Button onClick={capture} variant="success" size="lg" className="flex-1 text-base sm:text-lg">
              📸 CAPTURE
            </Button>
            <Button onClick={onClose} variant="secondary" size="lg" className="text-base sm:text-lg">
              CANCEL
            </Button>
          </div>
        ) : (
          <div className="space-y-2">
            <div className="flex gap-3">
              <Button onClick={capture} variant="primary" size="lg" className="flex-1 text-base sm:text-lg">
                📸 CAPTURE MORE
              </Button>
              <Button onClick={retake} variant="secondary" size="lg" className="text-base sm:text-lg">
                🔄 CLEAR
              </Button>
            </div>
            <Button onClick={confirmCapture} variant="success" size="lg" className="w-full text-base sm:text-lg">
              ✓ ANALYZE {capturedImages.length} PHOTO{capturedImages.length > 1 ? 'S' : ''}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};
