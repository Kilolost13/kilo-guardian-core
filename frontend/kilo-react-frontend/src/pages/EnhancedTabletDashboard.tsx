import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import SpeechRecognition, { useSpeechRecognition } from 'react-speech-recognition';
import { FaMicrophone, FaMicrophoneSlash, FaCamera, FaPaperclip, FaCog, FaUser, FaBrain, FaBell, FaChartLine, FaLightbulb, FaTrophy } from 'react-icons/fa';
import { chatService } from '../services/chatService';
import { Message, DashboardStats, RealTimeUpdate, CoachingInsight } from '../types';
import { CameraCapture } from '../components/shared/CameraCapture';
import { Button } from '../components/shared/Button';
import { Card } from '../components/shared/Card';

const EnhancedTabletDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [messages, setMessages] = useState<Message[]>([
    { id: '1', role: 'ai', content: "Good morning! How can I help you today?", timestamp: new Date() }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showCamera, setShowCamera] = useState(false);
  const [showPrescriptionScanner, setShowPrescriptionScanner] = useState(false);
  const [showVoiceInput, setShowVoiceInput] = useState(false);
  const [manualInputMode, setManualInputMode] = useState(false);
  const [prescriptionResult, setPrescriptionResult] = useState<any>(null);
  const [scanningPrescription, setScanningPrescription] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);

  // Enhanced state for tablet UI
  const [stats, setStats] = useState<DashboardStats>({
    totalMemories: 0,
    activeHabits: 0,
    completedGoals: 0,
    streakDays: 0,
    averageMood: 0,
    recentActivity: 0,
    activeGoals: 0,
    upcomingReminders: 0,
    monthlySpending: 0,
    insightsGenerated: 0,
    goalsProgress: 0
  });
  const [realTimeUpdates, setRealTimeUpdates] = useState<RealTimeUpdate[]>([]);
  const [insights, setInsights] = useState<CoachingInsight[]>([]);

  const {
    transcript,
    listening,
    resetTranscript,
    browserSupportsSpeechRecognition
  } = useSpeechRecognition();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (transcript && !listening) {
      setInput(transcript);
      handleVoiceSubmit(transcript);
    }
  }, [transcript, listening]);

  // Load dashboard data
  useEffect(() => {
    fetchDashboardData();
  }, []);

  // Cleanup camera stream on unmount
  useEffect(() => {
    return () => {
      if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
      }
    };
  }, [cameraStream]);

  const fetchDashboardData = async () => {
    try {
      // Mock data - replace with actual API calls
      setStats({
        totalMemories: 1247,
        activeHabits: 5,
        completedGoals: 12,
        streakDays: 23,
        averageMood: 7.8,
        recentActivity: 45,
        activeGoals: 3,
        upcomingReminders: 2,
        monthlySpending: 1250.50,
        insightsGenerated: 89,
        goalsProgress: 68
      });

      setRealTimeUpdates([
        {
          id: '1',
          type: 'memory_added',
          message: 'New memory added to your knowledge base',
          timestamp: new Date().toISOString(),
          priority: 'medium'
        }
      ]);

      setInsights([
        {
          id: '1',
          type: 'motivation',
          title: 'Great Progress!',
          description: 'You\'ve maintained your exercise habit for 23 days straight!',
          message: 'You\'ve maintained your exercise habit for 23 days straight!',
          priority: 'high',
          actionable: true,
          createdAt: new Date().toISOString()
        }
      ]);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await chatService.sendMessage(input);
      const aiContent = typeof response === 'string'
        ? response
        : (response && typeof response === 'object' && 'message' in response)
          ? (response as { message?: string }).message || JSON.stringify(response)
          : JSON.stringify(response);
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        content: aiContent,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, aiMessage]);
    } catch (error) {
      console.error('Failed to send message:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleVoiceSubmit = async (voiceText: string) => {
    if (!voiceText.trim()) return;
    setInput(voiceText);
    await sendMessage();
  };

  const startVoiceInput = () => {
    resetTranscript();
    SpeechRecognition.startListening({
      continuous: true,
      language: 'en-US'
    } as any);
    setShowVoiceInput(true);
  };

  const stopVoiceInput = () => {
    SpeechRecognition.stopListening();
    setShowVoiceInput(false);
  };

  const handleReceiptCapture = async (imageBlob: Blob) => {
    setShowCamera(false);
    // Handle receipt processing
    alert('Receipt captured! Processing...');
  };

  // Prescription scanning functions
  const startPrescriptionScanning = async () => {
    setShowPrescriptionScanner(true);
    setPrescriptionResult(null);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'environment', // Prefer back camera
          width: { ideal: 1920 },
          height: { ideal: 1080 }
        }
      });

      setCameraStream(stream);

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    } catch (error) {
      console.error('Error accessing camera:', error);
      alert('Failed to access camera. Please grant camera permissions.');
      setShowPrescriptionScanner(false);
    }
  };

  const stopPrescriptionScanning = () => {
    if (cameraStream) {
      cameraStream.getTracks().forEach(track => track.stop());
      setCameraStream(null);
    }
    setShowPrescriptionScanner(false);
    setPrescriptionResult(null);
  };

  const capturePrescription = async () => {
    if (!videoRef.current || !canvasRef.current) return;

    setScanningPrescription(true);

    try {
      const video = videoRef.current;
      const canvas = canvasRef.current;

      // Set canvas dimensions to video dimensions
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;

      // Draw video frame to canvas
      const ctx = canvas.getContext('2d');
      if (!ctx) {
        throw new Error('Failed to get canvas context');
      }

      ctx.drawImage(video, 0, 0);

      // Convert canvas to blob
      const blob = await new Promise<Blob>((resolve, reject) => {
        canvas.toBlob((blob) => {
          if (blob) resolve(blob);
          else reject(new Error('Failed to create image blob'));
        }, 'image/jpeg', 0.95);
      });

      // Send to prescription analysis API
      const formData = new FormData();
      formData.append('image', blob, 'prescription.jpg');

      const response = await fetch('/api/ai_brain/analyze/prescription', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error(`API request failed: ${response.statusText}`);
      }

      const result = await response.json();
      setPrescriptionResult(result);

      // Stop camera stream after successful capture
      if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        setCameraStream(null);
      }

    } catch (error) {
      console.error('Error capturing prescription:', error);
      alert('Failed to analyze prescription. Please try again.');
    } finally {
      setScanningPrescription(false);
    }
  };

  const quickActions = [
    { icon: '💊', label: 'MEDS', path: '/medications', color: 'bg-blue-500' },
    { icon: '🔔', label: 'REMINDERS', path: '/reminders', color: 'bg-green-500' },
    { icon: '💰', label: 'FINANCE', path: '/finance', color: 'bg-yellow-500' },
    { icon: '✓', label: 'HABITS', path: '/habits', color: 'bg-purple-500' }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 p-4">
      {/* Header */}
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-3xl font-bold text-white flex items-center gap-3">
          {React.createElement(FaBrain as any, { className: 'text-blue-400 text-4xl' })}
          KILO AI MEMORY ASSISTANT
        </h1>
        <div className="flex items-center gap-4">
          <Button
            onClick={startPrescriptionScanning}
            variant="primary"
            size="lg"
            className="h-16 px-6 flex items-center gap-3 text-xl bg-green-600 hover:bg-green-700"
          >
            <span className="text-2xl">💊</span>
            SCAN PRESCRIPTION
          </Button>
          <Button
            onClick={() => navigate('/admin')}
            variant="secondary"
            size="sm"
            className="flex items-center gap-2"
          >
            {React.createElement(FaUser as any, null)}
            Admin
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Chat Area - REDUCED HEIGHT FOR LANDSCAPE */}
        <div className="lg:col-span-2">
          <Card className="h-[400px] flex flex-col">
            <div className="flex-1 overflow-y-auto p-4 space-y-4" ref={messagesEndRef}>
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] p-4 rounded-2xl ${
                      message.role === 'user'
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-900'
                    }`}
                  >
                    <p className="text-lg">{message.content}</p>
                    <p className="text-xs opacity-70 mt-2">
                      {message.timestamp.toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 p-4 rounded-2xl">
                    <div className="flex items-center gap-2">
                      <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                      <span className="text-gray-600">AI is thinking...</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Input Area - Enhanced for tablet */}
            <div className="border-t border-gray-200 p-4">
              {!manualInputMode ? (
                <div className="flex gap-3">
                  <Button
                    onClick={listening ? stopVoiceInput : startVoiceInput}
                    variant={listening ? "primary" : "secondary"}
                    size="lg"
                    className="flex-1 h-16 text-xl flex items-center justify-center gap-3"
                  >
                    {listening ? React.createElement(FaMicrophone as any, { className: 'text-2xl' }) : React.createElement(FaMicrophoneSlash as any, { className: 'text-2xl' })}
                    {listening ? 'Listening...' : 'Tap to Speak'}
                  </Button>
                  <Button
                    onClick={() => setShowCamera(true)}
                    variant="secondary"
                    size="lg"
                    className="h-16 w-16 flex items-center justify-center text-2xl"
                  >
                    {React.createElement(FaCamera as any, null)}
                  </Button>
                  <Button
                    onClick={() => setManualInputMode(true)}
                    variant="outline"
                    size="lg"
                    className="h-16 px-6 flex items-center justify-center text-xl"
                  >
                    ✏️ Type
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                      placeholder="Type your message here..."
                      className="flex-1 p-4 text-xl border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <Button
                      onClick={sendMessage}
                      variant="primary"
                      size="lg"
                      disabled={!input.trim() || loading}
                      className="px-8 h-16 text-xl"
                    >
                      Send
                    </Button>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      onClick={() => setManualInputMode(false)}
                      variant="secondary"
                      size="sm"
                      className="flex items-center gap-2"
                    >
                      🎤 Voice
                    </Button>
                    <Button
                      onClick={() => setShowCamera(true)}
                      variant="secondary"
                      size="sm"
                      className="flex items-center gap-2"
                    >
                      {React.createElement(FaCamera as any, null)}
                      Camera
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      className="flex items-center gap-2"
                    >
                      {React.createElement(FaPaperclip as any, null)}
                      Attach
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </Card>
        </div>

        {/* Sidebar - Stats and Quick Actions */}
        <div className="space-y-4">
          {/* Quick Actions - Large tablet-friendly buttons */}
          <Card>
            <h3 className="text-xl font-semibold text-white mb-4">Quick Actions</h3>
            <div className="grid grid-cols-2 gap-3">
              {quickActions.map((action, index) => (
                <Button
                  key={index}
                  onClick={() => navigate(action.path)}
                  variant="secondary"
                  size="lg"
                  className={`h-20 flex flex-col items-center justify-center text-white ${action.color} hover:opacity-80`}
                >
                  <span className="text-3xl mb-1">{action.icon}</span>
                  <span className="text-sm font-medium">{action.label}</span>
                </Button>
              ))}
            </div>
          </Card>

          {/* Real-time Updates */}
          <Card>
            <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
              {React.createElement(FaBell as any, { className: 'text-yellow-400' })}
              Real-time Updates
            </h3>
            <div className="space-y-2 max-h-40 overflow-y-auto">
              {realTimeUpdates.map((update) => (
                <div key={update.id} className="bg-blue-900/20 border border-blue-600/30 rounded-lg p-3">
                  <p className="text-sm text-blue-200">{update.message}</p>
                  <p className="text-xs text-blue-400 mt-1">
                    {new Date(update.timestamp).toLocaleTimeString()}
                  </p>
                </div>
              ))}
            </div>
          </Card>

          {/* AI Coaching */}
          <Card>
            <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
              {React.createElement(FaLightbulb as any, { className: 'text-purple-400' })}
              AI Coaching
            </h3>
            <div className="space-y-3 max-h-40 overflow-y-auto">
              {insights.map((insight) => (
                <div key={insight.id} className="bg-purple-900/20 border border-purple-600/30 rounded-lg p-3">
                  <h4 className="font-semibold text-purple-200">{insight.title}</h4>
                  <p className="text-sm text-purple-300 mt-1">{insight.description}</p>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>

      {/* Prescription Scanner Modal - FULL SCREEN */}
      {showPrescriptionScanner && (
        <div className="fixed inset-0 bg-black z-50 flex flex-col">
          {/* Header */}
          <div className="bg-gradient-to-r from-green-600 to-green-700 p-4 flex justify-between items-center">
            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
              <span className="text-3xl">💊</span>
              Scan Prescription
            </h2>
            <Button
              onClick={stopPrescriptionScanning}
              variant="danger"
              size="lg"
              className="px-6 h-14 text-xl"
            >
              ✕ Close
            </Button>
          </div>

          {!prescriptionResult ? (
            <>
              {/* Camera Preview */}
              <div className="flex-1 relative bg-black">
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  className="w-full h-full object-contain"
                />

                {/* Overlay guide */}
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                  <div className="border-4 border-green-400 border-dashed rounded-2xl w-[80%] h-[60%] flex items-center justify-center">
                    <p className="text-white text-2xl bg-black/50 px-6 py-3 rounded-lg">
                      Position prescription bottle or label here
                    </p>
                  </div>
                </div>
              </div>

              {/* Capture Button */}
              <div className="p-6 bg-gray-900 flex justify-center">
                <Button
                  onClick={capturePrescription}
                  variant="primary"
                  size="lg"
                  disabled={scanningPrescription}
                  className="h-20 px-12 text-2xl bg-green-600 hover:bg-green-700 flex items-center gap-3"
                >
                  {scanningPrescription ? (
                    <>
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white"></div>
                      Processing...
                    </>
                  ) : (
                    <>
                      📷 CAPTURE & ANALYZE
                    </>
                  )}
                </Button>
              </div>
            </>
          ) : (
            /* Results Display */
            <div className="flex-1 overflow-y-auto p-6 bg-gray-900">
              <div className="max-w-4xl mx-auto space-y-6">
                <div className="bg-green-900/30 border-2 border-green-600 rounded-2xl p-6">
                  {prescriptionResult.success ? (
                    <>
                      <h3 className="text-3xl font-bold text-green-400 mb-4">✓ Prescription Analyzed</h3>

                      {/* Extracted Text */}
                      {prescriptionResult.ocr_text && (
                        <div className="bg-black/50 rounded-xl p-6 mb-6">
                          <h4 className="text-xl font-semibold text-white mb-3">📝 Extracted Text:</h4>
                          <pre className="text-lg text-gray-200 whitespace-pre-wrap font-mono">
                            {prescriptionResult.ocr_text}
                          </pre>
                        </div>
                      )}

                      {/* Parsed Medication Data */}
                      {prescriptionResult.parsed_data && (
                        <div className="bg-blue-900/30 border border-blue-600 rounded-xl p-6 mb-6">
                          <h4 className="text-xl font-semibold text-blue-300 mb-3">💊 Medication Information:</h4>
                          <div className="text-lg text-blue-200 space-y-3">
                            {prescriptionResult.parsed_data.medication_name && (
                              <div>
                                <span className="font-bold">Name:</span> {prescriptionResult.parsed_data.medication_name}
                              </div>
                            )}
                            {prescriptionResult.parsed_data.dosage && (
                              <div>
                                <span className="font-bold">Dosage:</span> {prescriptionResult.parsed_data.dosage}
                              </div>
                            )}
                            {prescriptionResult.parsed_data.schedule && (
                              <div>
                                <span className="font-bold">Schedule:</span> {prescriptionResult.parsed_data.schedule}
                              </div>
                            )}
                            {prescriptionResult.parsed_data.prescriber && (
                              <div>
                                <span className="font-bold">Prescriber:</span> {prescriptionResult.parsed_data.prescriber}
                              </div>
                            )}
                            {prescriptionResult.parsed_data.instructions && (
                              <div>
                                <span className="font-bold">Instructions:</span> {prescriptionResult.parsed_data.instructions}
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      {/* AI Interpretation */}
                      {prescriptionResult.ai_interpretation && (
                        <div className="bg-purple-900/30 border border-purple-600 rounded-xl p-6">
                          <h4 className="text-xl font-semibold text-purple-300 mb-3">🤖 AI Analysis:</h4>
                          <div className="text-base text-purple-200">
                            {prescriptionResult.ai_interpretation}
                          </div>
                        </div>
                      )}
                    </>
                  ) : (
                    <>
                      <h3 className="text-3xl font-bold text-red-400 mb-4">⚠️ Analysis Failed</h3>
                      <div className="bg-red-900/30 border border-red-600 rounded-xl p-6">
                        <p className="text-lg text-red-200">
                          {prescriptionResult.error || 'Failed to analyze prescription image. Please try again.'}
                        </p>
                      </div>
                    </>
                  )}

                  {/* Action Buttons */}
                  <div className="flex gap-4 mt-6">
                    <Button
                      onClick={startPrescriptionScanning}
                      variant="primary"
                      size="lg"
                      className="flex-1 h-16 text-xl"
                    >
                      📷 Scan Another
                    </Button>
                    <Button
                      onClick={stopPrescriptionScanning}
                      variant="secondary"
                      size="lg"
                      className="flex-1 h-16 text-xl"
                    >
                      ✓ Done
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Hidden canvas for image capture */}
          <canvas ref={canvasRef} className="hidden" />
        </div>
      )}

      {/* Receipt Camera Modal */}
      {showCamera && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-2xl max-w-md w-full mx-4">
            <CameraCapture onCapture={handleReceiptCapture} onClose={() => setShowCamera(false)} />
            <Button
              onClick={() => setShowCamera(false)}
              variant="secondary"
              className="w-full mt-4"
            >
              Cancel
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};

export default EnhancedTabletDashboard;
