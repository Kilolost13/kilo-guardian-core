export interface Message {
  id: string;
  role: 'user' | 'ai';
  content: string;
  timestamp: Date;
}

export interface Medication {
  id: number;
  name: string;
  dosage: string;
  schedule: string;
  prescriber: string;
  instructions: string;
  quantity: number;
  nextDose?: Date;
  taken?: boolean;
}

export interface Reminder {
  id: number;
  text: string;
  when: string;
  time: string;
  completed: boolean;
  recurring?: boolean;
  icon?: string;
}

export interface Transaction {
  id: number;
  amount: number;
  description: string;
  date: string;
  category: string;
}

export interface Budget {
  id?: number;
  category: string;
  monthly_limit: number;
  created_at?: string;
}

export interface Goal {
  id: string;
  title: string;
  name?: string; // For backward compatibility
  description: string;
  targetValue: number;
  target_amount?: number; // For backward compatibility
  currentValue: number;
  current_amount?: number; // For backward compatibility
  category: string;
  deadline?: string;
  completed: boolean;
  completedAt?: string;
  createdAt: string;
}

export interface Achievement {
  id: string;
  title: string;
  description: string;
  icon: string;
  unlockedAt: string;
  rarity: 'common' | 'rare' | 'epic' | 'legendary';
}

export interface ProgressStats {
  totalMemories: number;
  activeGoals: number;
  completedGoals: number;
  streakDays: number;
  averageMood: number;
}

export interface ProgressData {
  goals: Goal[];
  achievements: Achievement[];
  stats: ProgressStats;
}

// Missing types that are being imported
export interface SystemStatus {
  status: 'online' | 'offline' | 'maintenance';
  uptime: number;
  memoryUsage: number;
  cpuUsage: number;
  lastBackup?: string;
  gateway: boolean;
  ai_brain: boolean;
  meds: boolean;
  reminders: boolean;
  finance: boolean;
  habits: boolean;
}

export interface CoachingInsight {
  id: string;
  type: 'habit' | 'goal' | 'memory' | 'general' | 'celebration' | 'warning' | 'suggestion' | 'motivation' | 'reminder';
  title: string;
  description: string;
  message?: string; // For backward compatibility
  priority: 'low' | 'medium' | 'high';
  actionable: boolean;
  createdAt: string;
}

export interface DashboardStats {
  totalMemories: number;
  activeGoals: number;
  completedGoals: number;
  streakDays: number;
  averageMood: number;
  recentActivity: number;
  activeHabits: number;
  upcomingReminders: number;
  monthlySpending: number;
  insightsGenerated: number;
  goalsProgress: number;
}

export interface MemoryVisualization {
  categories: Array<{
    name: string;
    count: number;
    color: string;
  }>;
  timeline: Array<{
    date: string;
    count: number;
  }>;
  connections: Array<{
    from: string;
    to: string;
    strength: number;
  }>;
}

export interface RealTimeUpdate {
  id: string;
  type: 'memory_added' | 'insight_generated' | 'goal_completed' | 'habit_tracked' | 'goal_progress' | 'reminder_due';
  message: string;
  timestamp: string;
  priority: 'low' | 'medium' | 'high';
}

export interface UploadImageResult {
  description?: string;
  id?: string;
  url?: string;
  // Additional fields returned by the AI brain
  [key: string]: unknown;
}

export interface Habit {
  id: string;
  name: string;
  description: string;
  frequency: 'daily' | 'weekly' | 'monthly';
  targetCount: number;
  target_count?: number; // For backward compatibility
  currentCount: number;
  current_count?: number; // For backward compatibility
  streak: number;
  lastCompleted?: string;
  createdAt: string;
  category: string;
  completions?: Array<{
    completion_date: string;
    count: number;
  }>; // For backward compatibility
}

export interface MemoryNode {
  id: string;
  type: 'person' | 'event' | 'concept' | 'location' | 'object' | 'conversation' | 'medication' | 'habit' | 'finance' | 'reminder' | 'knowledge';
  label: string;
  content: string;
  importance: number;
  connections: string[];
  timestamp?: string; // For backward compatibility
  createdAt: string;
  updatedAt: string;
}

export interface KnowledgeGraph {
  nodes: MemoryNode[];
  edges: Array<{
    from: string;
    to: string;
    type: 'related' | 'caused' | 'located_at' | 'belongs_to' | 'similar_to';
    strength: number;
    label?: string; // For backward compatibility
  }>;
}

export interface VoiceCommand {
  id?: string;
  command: string;
  confidence: number;
  timestamp?: string;
  processed?: boolean;
  intent?: string;
  entities?: Record<string, any>;
}
