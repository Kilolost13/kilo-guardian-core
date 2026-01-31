import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/shared/Button';
import { Card } from '../components/shared/Card';
import { Habit } from '../types';
import api from '../services/api';

interface HabitPrediction {
  habit_id: number;
  completion_probability: number;
  confidence: string;
  recommendation: string;
  should_send_reminder: boolean;
}

interface OptimalTiming {
  habit_id: number;
  optimal_times: string[];
  reasoning: string;
}

const Habits: React.FC = () => {
  const navigate = useNavigate();
  const [habits, setHabits] = useState<Habit[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddHabit, setShowAddHabit] = useState(false);
  const [editingHabit, setEditingHabit] = useState<Habit | null>(null);
  const [predictions, setPredictions] = useState<Map<string, HabitPrediction>>(new Map());
  const [timings, setTimings] = useState<Map<string, OptimalTiming>>(new Map());
  const [habitForm, setHabitForm] = useState<{ name: string; frequency: 'daily'|'weekly'|'monthly'; target_count: string | number }>({
    name: '',
    frequency: 'daily',
    target_count: '1'
  });
  const [suggestedTimes, setSuggestedTimes] = useState<string[]>([]);
  const [suggestionReasoning, setSuggestionReasoning] = useState<string>('');

  const fetchMLPredictions = React.useCallback(async (habitsData: Habit[]) => {
    try {
      const newPredictions = new Map<string, HabitPrediction>();
      const newTimings = new Map<string, OptimalTiming>();

      for (const habit of habitsData) {
        const streak = getStreak(habit);
        const completionsThisWeek = getCompletionsThisWeek(habit);

        // Fetch completion probability
        try {
          const predResponse = await api.post('/ml/predict/habit_completion', {
            habit_id: habit.id,
            habit_name: habit.name,
            current_streak: streak,
            completions_this_week: completionsThisWeek,
            target_count: habit.target_count,
            frequency: habit.frequency
          });
          newPredictions.set(habit.id, predResponse.data);
        } catch (error) {
          console.error(`Failed to fetch prediction for habit ${habit.id}:`, error);
        }

        // Fetch optimal reminder timing
        try {
          const timingResponse = await api.post('/ml/predict/reminder_timing', {
            habit_id: habit.id,
            habit_name: habit.name
          });
          newTimings.set(habit.id, timingResponse.data);
        } catch (error) {
          console.error(`Failed to fetch timing for habit ${habit.id}:`, error);
        }
      }

      setPredictions(newPredictions);
      setTimings(newTimings);
    } catch (error) {
      console.error('Failed to fetch ML predictions:', error);
    }
  }, []);

  const fetchHabits = React.useCallback(async () => {
    try {
      const response = await api.get('/habits');
      const habitsData = response.data;
      setHabits(habitsData);

      // Fetch ML predictions for each habit
      fetchMLPredictions(habitsData);
    } catch (error) {
      console.error('Failed to fetch habits:', error);
    } finally {
      setLoading(false);
    }
  }, [fetchMLPredictions]);

  useEffect(() => {
    fetchHabits();
  }, [fetchHabits]);



  const getCompletionsThisWeek = (habit: Habit): number => {
    const completions = habit.completions ?? [];
    if (completions.length === 0) return 0;

    const today = new Date();
    const weekAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);

    return completions.filter((c) => {
      const completionDate = new Date(c.completion_date);
      return completionDate >= weekAgo;
    }).length;
  };

  const completeHabit = async (id: number) => {
    try {
      await api.post(`/habits/complete/${id}`);
      fetchHabits();
    } catch (error) {
      console.error('Failed to complete habit:', error);
    }
  };

  const fetchSuggestedTimes = async (habitName: string) => {
    if (!habitName || habitName.length < 3) {
      setSuggestedTimes([]);
      setSuggestionReasoning('');
      return;
    }

    try {
      const response = await api.post('/ml/predict/reminder_timing', {
        habit_id: null,
        habit_name: habitName
      });
      setSuggestedTimes(response.data.optimal_times || []);
      setSuggestionReasoning(response.data.reasoning || '');
    } catch (error) {
      console.error('Failed to fetch suggested times:', error);
      setSuggestedTimes([]);
      setSuggestionReasoning('');
    }
  };

  const handleAddHabit = async () => {
    try {
      if (!habitForm.name) {
        alert('Please enter a habit name');
        return;
      }
      await api.post('/habits', {
        name: habitForm.name,
        frequency: habitForm.frequency,
        target_count: parseInt(String(habitForm.target_count), 10) || 1,
        active: true
      });
      setShowAddHabit(false);
      setHabitForm({ name: '', frequency: 'daily', target_count: 1 });
      setSuggestedTimes([]);
      setSuggestionReasoning('');
      fetchHabits();
    } catch (error) {
      console.error('Failed to add habit:', error);
      alert('Failed to add habit');
    }
  };

  const startEdit = (habit: Habit) => {
    setEditingHabit(habit);
    setHabitForm({
      name: habit.name || '',
      frequency: habit.frequency || 'daily',
      target_count: habit.target_count || 1
    });
  };

  const saveEdit = async () => {
    if (!editingHabit) return;
    try {
      await api.put(`/habits/${editingHabit.id}`, {
        name: habitForm.name,
        frequency: habitForm.frequency,
        target_count: parseInt(String(habitForm.target_count), 10) || 1,
        active: true
      });
      setEditingHabit(null);
      setHabitForm({ name: '', frequency: 'daily', target_count: 1 });
      fetchHabits();
    } catch (error) {
      console.error('Failed to update habit:', error);
      alert('Failed to update habit');
    }
  };

  const deleteHabit = async (id: number, name: string) => {
    if (!window.confirm(`Are you sure you want to delete "${name}"?`)) return;
    try {
      await api.delete(`/habits/${id}`);
      fetchHabits();
    } catch (error) {
      console.error('Failed to delete habit:', error);
      alert('Failed to delete habit');
    }
  };

  const getTodayCompletionCount = (habit: Habit): number => {
    const completions = habit.completions ?? [];
    if (completions.length === 0) return 0;
    const today = new Date().toISOString().split('T')[0];
    const todayCompletion = completions.find((c) => c.completion_date === today);
    return todayCompletion?.count ?? 0;
  };

  const getStreak = (habit: Habit): number => {
    const completions = habit.completions ?? [];
    if (completions.length === 0) return 0;

    const dates = completions.map((c) => c.completion_date);
    const uniqueDates = Array.from(new Set(dates));
    const completionDates = uniqueDates.sort().reverse();
    let streak = 0;
    const today = new Date();

    for (let i = 0; i < completionDates.length; i++) {
      const checkDate = new Date(today);
      checkDate.setDate(today.getDate() - i);
      const checkDateStr = checkDate.toISOString().split('T')[0];

      if (completionDates.includes(checkDateStr)) {
        streak++;
      } else {
        break;
      }
    }

    return streak;
  };

  const habitIcons = ['💧', '🏃', '📚', '🧘', '🍎', '💪', '🛌', '🧠', '🎯', '✨'];

  return (
    <div className="min-h-screen zombie-gradient p-2">
      <div className="flex justify-between items-center mb-2">
        <h1 className="text-xl font-bold text-zombie-green terminal-glow">✓ HABITS</h1>
        <Button onClick={() => navigate('/dashboard')} variant="secondary" size="sm">
          ← BACK
        </Button>
      </div>

      <div className="mb-2">
        <Button
          onClick={() => setShowAddHabit(true)}
          variant="success"
          size="md"
          className="w-full"
        >
          ➕ ADD HABIT
        </Button>
      </div>

      <div className="space-y-2">
        <h2 className="text-base font-semibold text-zombie-green terminal-glow">TODAY'S HABITS:</h2>
        {loading ? (
          <div className="text-center py-4 text-zombie-green">Loading habits...</div>
        ) : habits.length === 0 ? (
          <Card>
            <p className="text-center text-zombie-green">No habits tracked yet. Click "ADD HABIT" to start!</p>
          </Card>
        ) : (
          habits.map((habit) => {
            const completionCount = getTodayCompletionCount(habit);
            const progress = (completionCount / habit.target_count) * 100;
            const streak = getStreak(habit);
            const isCompleted = completionCount >= habit.target_count;

            return (
              <Card key={habit.id} className={`py-2 px-3 ${isCompleted ? 'bg-green-50' : ''}`}>
                <div className="flex justify-between items-start gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-3xl">{habitIcons[parseInt(habit.id) % habitIcons.length]}</span>
                      <div>
                        <h3 className="text-lg font-bold text-gray-800">{habit.name}</h3>
                        <p className="text-xs text-gray-600">{habit.frequency} • Target: {habit.target_count}x</p>
                      </div>
                    </div>

                    {/* Progress Bar */}
                    <div className="my-2">
                      <div className="flex justify-between text-xs text-gray-600 mb-1">
                        <span>Progress: {completionCount} / {habit.target_count}</span>
                        <span>{Math.min(Math.round(progress), 100)}%</span>
                      </div>
                      <div className="w-full bg-gray-300 rounded-full h-4">
                        <div
                          className={`h-4 rounded-full transition-all ${isCompleted ? 'bg-green-600' : 'bg-blue-600'}`}
                          style={{ width: `${Math.min(progress, 100)}%` }}
                        ></div>
                      </div>
                    </div>

                    {/* Streak */}
                    {streak > 0 && (
                      <div className="flex items-center gap-1 text-sm font-bold text-orange-600">
                        🔥 {streak} day streak
                      </div>
                    )}

                    {/* ML Prediction */}
                    {predictions.get(habit.id) && (
                      <div className="mt-2 p-2 bg-blue-50 rounded border border-blue-200">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-lg">🤖</span>
                          <div className="flex-1">
                            <div className="text-xs font-bold text-blue-800">
                              Kilo's Prediction: {Math.round(predictions.get(habit.id)!.completion_probability * 100)}% likely to complete
                            </div>
                            <div className="text-xs text-blue-600 mt-1">
                              {predictions.get(habit.id)!.recommendation}
                            </div>
                          </div>
                        </div>
                        {timings.get(habit.id) && timings.get(habit.id)!.optimal_times.length > 0 && (
                          <div className="text-xs text-blue-700 mt-1 border-t border-blue-200 pt-1">
                            ⏰ Best reminder times: {timings.get(habit.id)!.optimal_times.join(', ')}
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="flex flex-col gap-1">
                    <Button
                      onClick={() => startEdit(habit)}
                      variant="primary"
                      size="sm"
                      className="text-xs px-2 py-1"
                    >
                      ✏️
                    </Button>
                    <Button
                      onClick={() => deleteHabit(parseInt(habit.id), habit.name)}
                      variant="secondary"
                      size="sm"
                      className="text-xs px-2 py-1"
                    >
                      🗑️
                    </Button>
                    <Button
                      onClick={() => completeHabit(parseInt(habit.id))}
                      variant={isCompleted ? 'secondary' : 'success'}
                      size="lg"
                      disabled={isCompleted}
                      className="text-xs"
                    >
                      {isCompleted ? '✓ DONE' : 'DO IT'}
                    </Button>
                  </div>
                </div>
              </Card>
            );
          })
        )}
      </div>

      {/* Add Habit Modal */}
      {showAddHabit && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center p-4 z-50">
          <Card className="w-full max-w-2xl">
            <h2 className="text-2xl font-bold text-zombie-green terminal-glow mb-4">➕ ADD HABIT</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-zombie-green font-semibold mb-1">Habit Name:</label>
                <input
                  type="text"
                  value={habitForm.name}
                  onChange={(e) => {
                    setHabitForm({ ...habitForm, name: e.target.value });
                    fetchSuggestedTimes(e.target.value);
                  }}
                  className="w-full p-2 bg-gray-800 border border-zombie-green text-zombie-green rounded"
                  placeholder="e.g., Drink Water, Exercise, Read"
                />
              </div>

              {/* Kilo's Suggested Reminder Times */}
              {suggestedTimes.length > 0 && (
                <div className="bg-blue-900 bg-opacity-50 border-2 border-blue-500 rounded-lg p-3">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-2xl">🤖</span>
                    <h3 className="text-sm font-bold text-blue-300">KILO'S SUGGESTED REMINDER TIMES:</h3>
                  </div>
                  <div className="flex flex-wrap gap-2 mb-2">
                    {suggestedTimes.map((time, idx) => (
                      <span key={idx} className="bg-blue-600 text-white px-3 py-1 rounded-full text-sm font-semibold">
                        ⏰ {time}
                      </span>
                    ))}
                  </div>
                  {suggestionReasoning && (
                    <p className="text-xs text-blue-200">💡 {suggestionReasoning}</p>
                  )}
                </div>
              )}

              <div>
                <label className="block text-zombie-green font-semibold mb-1">Frequency:</label>
                <select
                  value={habitForm.frequency}
                  onChange={(e) => setHabitForm({ ...habitForm, frequency: e.target.value as 'daily'|'weekly'|'monthly' })}
                  className="w-full p-2 bg-gray-800 border border-zombie-green text-zombie-green rounded"
                >
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                </select>
              </div>
              <div>
                <label className="block text-zombie-green font-semibold mb-1">Target Count (per day):</label>
                <input
                  type="number"
                  min="1"
                  value={habitForm.target_count}
                  onChange={(e) => setHabitForm({ ...habitForm, target_count: parseInt(e.target.value) || 1 })}
                  className="w-full p-2 bg-gray-800 border border-zombie-green text-zombie-green rounded"
                  placeholder="e.g., 8 (glasses of water)"
                />
              </div>
              <div className="flex gap-3 mt-4">
                <Button onClick={handleAddHabit} variant="success" size="lg" className="flex-1">
                  💾 SAVE
                </Button>
                <Button onClick={() => setShowAddHabit(false)} variant="secondary" size="lg" className="flex-1">
                  CANCEL
                </Button>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Edit Habit Modal */}
      {editingHabit && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center p-4 z-50">
          <Card className="w-full max-w-2xl">
            <h2 className="text-2xl font-bold text-zombie-green terminal-glow mb-4">✏️ EDIT HABIT</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-zombie-green font-semibold mb-1">Habit Name:</label>
                <input
                  type="text"
                  value={habitForm.name}
                  onChange={(e) => setHabitForm({ ...habitForm, name: e.target.value })}
                  className="w-full p-2 bg-gray-800 border border-zombie-green text-zombie-green rounded"
                />
              </div>
              <div>
                <label className="block text-zombie-green font-semibold mb-1">Frequency:</label>
                <select
                  value={habitForm.frequency}
                  onChange={(e) => setHabitForm({ ...habitForm, frequency: e.target.value as 'daily'|'weekly'|'monthly' })}
                  className="w-full p-2 bg-gray-800 border border-zombie-green text-zombie-green rounded"
                >
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                </select>
              </div>
              <div>
                <label className="block text-zombie-green font-semibold mb-1">Target Count (per day):</label>
                <input
                  type="number"
                  min="1"
                  value={habitForm.target_count}
                  onChange={(e) => setHabitForm({ ...habitForm, target_count: parseInt(e.target.value) || 1 })}
                  className="w-full p-2 bg-gray-800 border border-zombie-green text-zombie-green rounded"
                />
              </div>
              <div className="flex gap-3 mt-4">
                <Button onClick={saveEdit} variant="success" size="lg" className="flex-1">
                  💾 SAVE
                </Button>
                <Button onClick={() => setEditingHabit(null)} variant="secondary" size="lg" className="flex-1">
                  CANCEL
                </Button>
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
};

export default Habits;
