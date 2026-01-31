import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/shared/Button';
import { Card } from '../components/shared/Card';
import api from '../services/api';

interface Reminder {
  id: number;
  title: string;
  description: string;
  reminder_time: string;
  recurring: boolean;
  created_at?: string;
}

const Reminders: React.FC = () => {
  const navigate = useNavigate();
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddReminder, setShowAddReminder] = useState(false);
  const [reminderForm, setReminderForm] = useState({
    title: '',
    description: '',
    reminder_time: '',
    recurring: false
  });

  useEffect(() => {
    fetchReminders();
  }, []);

  const fetchReminders = async () => {
    try {
      setLoading(true);
      const response = await api.get('/reminder/reminders');
      setReminders(response.data.reminders || []);
    } catch (error) {
      console.error('Failed to fetch reminders:', error);
      setReminders([]);
    } finally {
      setLoading(false);
    }
  };

  const handleAddReminder = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/reminder/reminders', reminderForm);
      setShowAddReminder(false);
      setReminderForm({ title: '', description: '', reminder_time: '', recurring: false });
      fetchReminders();
    } catch (error) {
      console.error('Failed to add reminder:', error);
    }
  };

  const handleDeleteReminder = async (id: number) => {
    try {
      await api.delete(`/reminder/reminders/${id}`);
      fetchReminders();
    } catch (error) {
      console.error('Failed to delete reminder:', error);
    }
  };

  const formatReminderTime = (time: string) => {
    try {
      return new Date(time).toLocaleString();
    } catch {
      return time;
    }
  };

  return (
    <div className="min-h-screen zombie-gradient p-2">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              onClick={() => navigate('/dashboard')}
              size="sm"
            >
              ← BACK
            </Button>
            <h1 className="text-xl font-bold text-zombie-green terminal-glow">🔔 REMINDERS</h1>
          </div>
          <Button
            variant="primary"
            onClick={() => setShowAddReminder(!showAddReminder)}
          >
            {showAddReminder ? 'Cancel' : '+ Add Reminder'}
          </Button>
        </div>

        {/* Add Reminder Form */}
        {showAddReminder && (
          <Card className="mb-2 py-3 px-4">
            <form onSubmit={handleAddReminder} className="space-y-3">
              <h2 className="text-lg font-bold text-zombie-green terminal-glow mb-3">CREATE NEW REMINDER</h2>

              <div>
                <label className="block text-sm font-semibold text-zombie-green mb-1">
                  Title *
                </label>
                <input
                  type="text"
                  required
                  value={reminderForm.title}
                  onChange={(e) => setReminderForm({ ...reminderForm, title: e.target.value })}
                  className="w-full p-2 bg-zombie-dark text-zombie-green border-2 border-zombie-green rounded terminal-text"
                  placeholder="e.g., Take medication"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-zombie-green mb-1">
                  Description
                </label>
                <textarea
                  value={reminderForm.description}
                  onChange={(e) => setReminderForm({ ...reminderForm, description: e.target.value })}
                  className="w-full p-2 bg-zombie-dark text-zombie-green border-2 border-zombie-green rounded terminal-text"
                  placeholder="Optional details..."
                  rows={2}
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-zombie-green mb-1">
                  Reminder Time *
                </label>
                <input
                  type="datetime-local"
                  required
                  value={reminderForm.reminder_time}
                  onChange={(e) => setReminderForm({ ...reminderForm, reminder_time: e.target.value })}
                  className="w-full p-2 bg-zombie-dark text-zombie-green border-2 border-zombie-green rounded terminal-text"
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="recurring"
                  checked={reminderForm.recurring}
                  onChange={(e) => setReminderForm({ ...reminderForm, recurring: e.target.checked })}
                  className="w-4 h-4"
                />
                <label htmlFor="recurring" className="text-sm font-semibold text-zombie-green">
                  Recurring reminder
                </label>
              </div>

              <div className="flex gap-3">
                <button
                  type="submit"
                  className="flex-1 px-6 py-3 bg-green-500 text-white font-semibold rounded-lg hover:bg-green-600 transition-all min-h-[56px]"
                >
                  Create Reminder
                </button>
                <Button
                  variant="secondary"
                  onClick={() => setShowAddReminder(false)}
                  className="flex-1"
                >
                  Cancel
                </Button>
              </div>
            </form>
          </Card>
        )}

        {/* Reminders List */}
        <div className="mb-2">
          <h2 className="text-base font-semibold text-zombie-green terminal-glow mb-2">ACTIVE REMINDERS:</h2>
        </div>
        {loading ? (
          <div className="text-center py-4 text-zombie-green">Loading reminders...</div>
        ) : reminders.length === 0 ? (
          <Card className="py-3 px-4">
            <p className="text-center text-zombie-green">
              No reminders yet. Click "+ ADD REMINDER" to create one!
            </p>
          </Card>
        ) : (
          <div className="space-y-2">
            {reminders.map((reminder) => (
              <Card key={reminder.id} className="py-2 px-3">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="text-base font-bold text-zombie-green flex-1">
                    {reminder.title}
                  </h3>
                  <button
                    onClick={() => handleDeleteReminder(reminder.id)}
                    className="text-red-500 hover:text-red-700 text-xl"
                    title="Delete reminder"
                  >
                    ×
                  </button>
                </div>

                {reminder.description && (
                  <p className="text-zombie-green text-sm mb-2">{reminder.description}</p>
                )}

                <div className="space-y-1 text-xs">
                  <div className="flex items-center gap-2 text-zombie-green">
                    <span>⏰</span>
                    <span>{formatReminderTime(reminder.reminder_time)}</span>
                  </div>

                  {reminder.recurring && (
                    <div className="flex items-center gap-2 text-zombie-green">
                      <span>🔄</span>
                      <span>Recurring</span>
                    </div>
                  )}
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Reminders;
