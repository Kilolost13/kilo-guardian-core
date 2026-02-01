import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { chatService } from '../services/chatService';
import { Message } from '../types';
import { Button } from '../components/shared/Button';
import { Card } from '../components/shared/Card';
import { CameraCapture } from '../components/shared/CameraCapture';
import api from '../services/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { io } from 'socket.io-client';
import SpeechRecognition, { useSpeechRecognition } from 'react-speech-recognition';
import { RealTimeUpdate, CoachingInsight } from '../types';
import { useDeviceDetection } from '../utils/deviceDetection';

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [messages, setMessages] = useState<Message[]>([
    { id: '1', role: 'ai', content: "Hey Kyle! I'm Kilo, your AI assistant. How can I help you today?", timestamp: new Date() }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showCamera, setShowCamera] = useState(false);
  const [insights, setInsights] = useState<CoachingInsight[]>([]);
  const [stats, setStats] = useState<{
    totalMemories: number;
    activeHabits: number;
    upcomingReminders: number;
    monthlySpending: number;
    insightsGenerated: number;
  }>({ totalMemories: 0, activeHabits: 0, upcomingReminders: 0, monthlySpending: 0, insightsGenerated: 0 });
  const [memoryViz, setMemoryViz] = useState<{ timeline: { date: string; count: number }[]; categories: { name: string; count: number }[] }>({ timeline: [], categories: [] });

  // Real-time socket and updates
  const [realTimeUpdates, setRealTimeUpdates] = useState<{ type: string; message?: string }[]>([]);

  // Voice input (speech recognition)
  const [showVoiceInput, setShowVoiceInput] = useState(false);
  const {
    transcript,
    listening,
    resetTranscript,
    browserSupportsSpeechRecognition
  } = useSpeechRecognition();

  // Device detection
  const { deviceInfo, features } = useDeviceDetection();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  const handleVoiceSubmit = useCallback(async (voiceText: string) => {
    if (!voiceText.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: `🎤 ${voiceText}`,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setLoading(true);

    try {
      const response = await chatService.sendMessage(voiceText);
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        content: response,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, aiMessage]);
    } catch (error) {
      console.error('Failed to process voice input:', error);
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        content: "Sorry, I couldn't process your voice input.",
        timestamp: new Date(),
      }]);
    } finally {
      setLoading(false);
      resetTranscript();
      setShowVoiceInput(false);
    }
  }, [resetTranscript]);

  useEffect(() => {
    if (transcript && !listening) {
      handleVoiceSubmit(transcript);
    }
  }, [transcript, listening, handleVoiceSubmit]);

  const toggleVoiceInput = () => {
    if (!browserSupportsSpeechRecognition) {
      alert('Voice input is not supported in this browser.');
      return;
    }

    if (listening) {
      SpeechRecognition.stopListening();
      setShowVoiceInput(false);
    } else {
      resetTranscript();
      SpeechRecognition.startListening({ continuous: false });
      setShowVoiceInput(true);
    }
  }; 

  const scrollToBottom = () => {
    // Scroll only the chat container, not the entire window
    const container = messagesContainerRef.current;
    if (container) {
      container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
      return;
    }
    // Fallback: still try to scroll the marker into view
    const el = messagesEndRef.current;
    if (el && typeof el.scrollIntoView === 'function') {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    fetchInsights();
    fetchStats();
    fetchMemoryVisualization();
  }, []);

  useEffect(() => {
    const newSocket = io(process.env.REACT_APP_API_URL || window.location.origin, {
      path: '/api/socket.io',
      transports: ['websocket', 'polling']
    });

    newSocket.on('connect', () => {
      console.log('Connected to real-time updates');
    });

    newSocket.on('memory_update', (update: RealTimeUpdate) => {
      setRealTimeUpdates(prev => [update, ...prev].slice(0, 10));
      fetchStats();
    });

    newSocket.on('insight_generated', (insight: CoachingInsight) => {
      setInsights(prev => [insight, ...prev].slice(0, 5));
    });


    return () => {
      newSocket.close();
    };
  }, []);

  // Agent integration - poll for proactive agent messages
  useEffect(() => {
    const fetchAgentMessages = async () => {
      try {
        // Agent API runs on port 9200
        const response = await fetch('http://192.168.68.56:9200/agent/messages?since_minutes=1');
        const data = await response.json();

        if (data.messages && data.messages.length > 0) {
          // Add agent messages to chat
          const agentMessages: Message[] = data.messages.map((msg: any) => ({
            id: `agent-${msg.timestamp}`,
            role: 'ai' as const,
            content: `🤖 **KILO:** ${msg.content}`,
            timestamp: new Date(msg.timestamp)
          }));

          setMessages(prev => {
            // Avoid duplicates by checking if message already exists
            const existingIds = new Set(prev.map(m => m.id));
            const newMessages = agentMessages.filter(m => !existingIds.has(m.id));
            return [...prev, ...newMessages];
          });
        }
      } catch (error) {
        // Silently fail - agent API might not be available
        console.debug('Agent messages fetch skipped:', error);
      }
    };

    // Initial fetch
    fetchAgentMessages();

    // Poll every 30 seconds
    const interval = setInterval(fetchAgentMessages, 30000);

    return () => clearInterval(interval);
  }, []);

  const fetchInsights = async () => {
    try {
      const response = await api.get('/ml/insights/patterns');
      setInsights(response.data);
    } catch (error) {
      console.error('Failed to fetch insights:', error);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await api.get('/ai_brain/stats/dashboard');
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  const fetchMemoryVisualization = async () => {
    try {
      const response = await api.get('/ai_brain/memory/visualization');
      setMemoryViz(response.data);
    } catch (error) {
      console.error('Failed to fetch memory visualization:', error);
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
    const messageText = input;
    setInput('');
    setLoading(true);

    try {
      // Check if message is an agent command
      const agentKeywords = ['remind', 'spending', 'spend', 'money', 'budget', 'habit', 'med', 'medication', 'financial'];
      const isAgentCommand = agentKeywords.some(keyword =>
        messageText.toLowerCase().includes(keyword)
      );

      let response: string;

      if (isAgentCommand) {
        // Route to agent API
        try {
          const agentResponse = await fetch('http://192.168.68.56:9200/agent/command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              command: messageText,
              user: 'user'
            })
          });
          const agentData = await agentResponse.json();
          response = agentData.success ? agentData.message : 'Sorry, I couldn\'t process that command.';
        } catch (err) {
          // Fallback to regular chat if agent unavailable
          response = await chatService.sendMessage(messageText);
        }
      } else {
        // Regular AI chat
        response = await chatService.sendMessage(messageText);
      }

      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        content: response,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, aiMessage]);
    } catch (error) {
      console.error('Failed to send message:', error);
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date(),
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleImageCapture = async (blob: Blob, dataUrl: string) => {
    setShowCamera(false);
    setLoading(true);

    try {
      // Upload image to AI Brain
      const result = await chatService.uploadImage(blob, 'general');

      // Add user message showing the image
      const userMessage: Message = {
        id: Date.now().toString(),
        role: 'user',
        content: '📷 Image uploaded',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, userMessage]);

      // Add AI response
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        content: result.description || 'Image uploaded successfully!',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, aiMessage]);
    } catch (error) {
      console.error('Failed to upload image:', error);
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        content: 'Sorry, failed to process the image.',
        timestamp: new Date(),
      }]);
    } finally {
      setLoading(false);
    }
  };

  const quickActions = [
    { icon: '💊', label: 'MEDS', path: '/medications', bgColor: '#2563eb' }, // blue-600
    { icon: '🔔', label: 'REMINDERS', path: '/reminders', bgColor: '#9333ea' }, // purple-600
    { icon: '💰', label: 'FINANCE', path: '/finance', bgColor: '#16a34a' }, // green-600
    { icon: '✓', label: 'HABITS', path: '/habits', bgColor: '#ca8a04' }, // yellow-600
  ];

  return (
    <div className="min-h-screen zombie-gradient p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center gap-3">
          <h1 className="text-3xl font-bold text-zombie-green terminal-glow flex items-center gap-3">
            🧠 KILO AI MEMORY
          </h1>
          {/* Device indicator */}
          <span className="text-xs px-2 py-1 rounded-full bg-dark-border text-zombie-green border border-zombie-green">
            {deviceInfo.type === 'tablet' ? '📱 Tablet' : '💻 Server'}
          </span>
        </div>
        {features.showFullAdminPanel && (
          <Button onClick={() => navigate('/admin')} variant="secondary" size="sm">
            ⚙️ ADMIN
          </Button>
        )}
      </div>

      {/* Real-time updates banner */}
      {realTimeUpdates.length > 0 && (
        <Card className="mb-4 bg-blue-900 border-blue-600">
          <div className="flex items-center gap-2 text-blue-200 p-2">
            <span className="text-xl">🔔</span>
            <span className="text-sm">
              {realTimeUpdates[0].type === 'memory_update' && 'New memory added to your knowledge base'}
              {realTimeUpdates[0].type === 'insight_generated' && 'New AI insight generated'}
              {realTimeUpdates[0].type === 'goal_progress' && 'Goal progress updated'}
            </span>
          </div>
        </Card>
      )}

      {/* Chat Area */}
      <Card className="mb-6 h-[500px] flex flex-col">
        <div className="flex items-center justify-between mb-4 pb-4 border-b border-dark-border">
          <h2 className="text-xl font-semibold text-zombie-green terminal-glow flex items-center gap-2">
            💬 CHAT WITH YOUR AI MEMORY
          </h2>
        </div>

        {/* Messages */}
        <div ref={messagesContainerRef} className="flex-1 overflow-y-auto mb-4 space-y-4">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[70%] p-4 rounded-2xl border-2 ${
                  msg.role === 'user'
                    ? 'bg-zombie-green text-dark-bg border-zombie-green rounded-br-none'
                    : 'bg-dark-border text-zombie-green border-dark-border rounded-bl-none'
                }`}
              >
                <div className="flex items-start gap-2">
                  <span className="text-2xl">{msg.role === 'user' ? '👤' : '🤖'}</span>
                  <p className="text-lg leading-relaxed">{msg.content}</p>
                </div>
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-dark-border border-2 border-dark-border p-4 rounded-2xl rounded-bl-none">
                <div className="flex items-center gap-2">
                  <span className="text-2xl">🤖</span>
                  <div className="flex gap-1">
                    <div className="w-2 h-2 bg-zombie-green rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                    <div className="w-2 h-2 bg-zombie-green rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                    <div className="w-2 h-2 bg-zombie-green rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                  </div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="flex flex-col gap-2">
          {/* Voice status indicator */}
          {listening && (
            <div className="flex items-center gap-2 text-sm text-zombie-green animate-pulse">
              <div className="flex gap-1">
                <div className="w-1 h-4 bg-zombie-green rounded animate-pulse" style={{ animationDelay: '0ms' }}></div>
                <div className="w-1 h-6 bg-zombie-green rounded animate-pulse" style={{ animationDelay: '150ms' }}></div>
                <div className="w-1 h-5 bg-zombie-green rounded animate-pulse" style={{ animationDelay: '300ms' }}></div>
                <div className="w-1 h-7 bg-zombie-green rounded animate-pulse" style={{ animationDelay: '450ms' }}></div>
                <div className="w-1 h-4 bg-zombie-green rounded animate-pulse" style={{ animationDelay: '600ms' }}></div>
              </div>
              <span>🎤 Listening...</span>
            </div>
          )}
          {/* Character Counter */}
          <div className={`text-xs text-right mb-1 font-mono transition-colors ${
            input.length >= 1500 ? 'text-red-500 font-bold animate-pulse' : 
            input.length >= 1200 ? 'text-yellow-400' : 'text-gray-400'
          }`}>
            {input.length} / 1500 chars {input.length >= 1500 && '(MAX LIMIT)'}
          </div>
          <div className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => {
                const val = e.target.value;
                if (val.length <= 1500) setInput(val);
              }}
              onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
              placeholder={showVoiceInput ? "Listening..." : "Type your message or use voice..."}
              className={`flex-1 px-6 py-4 text-lg rounded-xl border-2 bg-dark-bg text-zombie-green placeholder-zombie-green placeholder-opacity-50 focus:outline-none transition-all ${
                input.length >= 1500 
                  ? 'border-red-500 focus:border-red-500' 
                  : 'border-dark-border focus:border-zombie-green'
              }`}
              disabled={loading}
            />
            <Button
              onClick={toggleVoiceInput}
              disabled={loading}
              size="lg"
              variant={listening ? 'primary' : 'secondary'}
              className={listening ? 'animate-pulse shadow-lg shadow-zombie-green/50' : ''}
            >
              {listening ? '🎙️' : '🎤'}
            </Button>
          {(features.showServerCamera || features.showTabletCamera) && (
            <Button onClick={() => setShowCamera(true)} variant="secondary" size="lg">
              📷
            </Button>
          )}
          <Button onClick={() => {}} variant="secondary" size="lg">
            📎
          </Button>
          </div>
        </div>
      </Card>

      {/* Dashboard Stats (from Enhanced) */}
      <Card className="mb-6">
        <h3 className="text-xl font-semibold text-zombie-green mb-3 flex items-center gap-2">
          💠 DASHBOARD STATS
        </h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-400">{stats.totalMemories}</div>
            <div className="text-sm text-gray-400">Memories</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-400">{stats.activeHabits}</div>
            <div className="text-sm text-gray-400">Active Habits</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-400">{stats.upcomingReminders}</div>
            <div className="text-sm text-gray-400">Reminders</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-yellow-400">${stats.monthlySpending}</div>
            <div className="text-sm text-gray-400">Monthly Spend</div>
          </div>
        </div>
      </Card>

      {/* Kilo's Insights Widget */}
      {insights.length > 0 && (
        <Card className="mb-6 bg-gradient-to-br from-blue-50 to-purple-50">
          <h3 className="text-xl font-semibold text-blue-800 mb-3 flex items-center gap-2">
            🤖 <span className="terminal-glow">KILO'S INSIGHTS</span>
          </h3>
          <div className="space-y-3">
            {insights.map((insight, idx) => (
              <div key={idx} className={`p-3 rounded-lg border-2 ${
                insight.actionable ? 'bg-green-50 border-green-300' : 'bg-blue-50 border-blue-300'
              }`}>
                <div className="flex items-start gap-3">
                          <span className="text-2xl">
                    {insight.type === 'celebration' && '🎉'}
                    {insight.type === 'warning' && '⚠️'}
                    {insight.type === 'suggestion' && '💡'}
                    {insight.type === 'motivation' && '🚀'}
                    {insight.type === 'reminder' && '🔔'}
                  </span>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-800">{insight.title || insight.description}</p>
                    <p className="text-xs text-gray-600 mt-1">{insight.message || insight.description}</p>
                    <div className="flex items-center gap-2 mt-1">
                      {insight.actionable && (
                        <span className="text-xs bg-green-600 text-white px-2 py-0.5 rounded-full">
                          Actionable
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Memory Activity Chart */}
      {memoryViz.timeline.length > 0 && (
        <Card className="mb-6">
          <h3 className="text-xl font-semibold text-zombie-green mb-3">Memory Activity</h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={memoryViz.timeline}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="date" stroke="#9CA3AF" fontSize={12} />
              <YAxis stroke="#9CA3AF" fontSize={12} />
              <Tooltip contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '8px' }} />
              <Line type="monotone" dataKey="count" stroke="#10B981" strokeWidth={2} dot={{ fill: '#10B981', strokeWidth: 2, r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      )}

      {/* Quick Actions */}
      <div>
        <h3 className="text-xl font-semibold text-zombie-green terminal-glow mb-4">QUICK ACTIONS:</h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 max-w-4xl mx-auto">
          {quickActions.map((action) => (
            <div
              key={action.path}
              onClick={() => navigate(action.path)}
              className="border-2 border-dark-border rounded-xl shadow-md p-4 cursor-pointer hover:scale-105 hover:shadow-lg hover:border-zombie-green transition-all text-center"
              style={{
                backgroundColor: action.bgColor,
                backgroundImage: 'none'
              }}
            >
              <div className="text-4xl mb-2">{action.icon}</div>
              <div className="text-sm font-semibold text-white">{action.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Camera Modal */}
      {showCamera && (
        <CameraCapture
          onCapture={handleImageCapture}
          onClose={() => setShowCamera(false)}
          type="general"
        />
      )}
    </div>
  );
};

export default Dashboard;
