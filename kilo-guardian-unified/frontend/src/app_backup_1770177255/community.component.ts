import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

interface ForumTopic {
  title: string;
  author: string;
  replies: number;
  active: string;
}

@Component({
  selector: 'app-community',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="h-full w-full p-4 md:p-6 lg:p-8 grid-bg overflow-y-auto">
      <div class="max-w-7xl mx-auto w-full">
        <h2 class="text-3xl md:text-4xl font-header text-white mb-2">The Barracks</h2>
        <p class="text-gray-400 mb-6 md:mb-8 border-l-2 border-[#39ff14] pl-4 text-sm md:text-base">Community Forum & Knowledge Base</p>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6 lg:gap-8">
          <div class="lg:col-span-2">
            <div class="bg-[#0a0a0a] border border-gray-800">
              <div class="bg-gray-900 px-4 py-2 border-b border-gray-800 flex justify-between items-center">
                <span class="text-[#39ff14] font-bold text-sm md:text-base">ACTIVE TRANSMISSIONS</span>
                <svg class="text-[#39ff14] animate-pulse" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="2"/>
                  <path d="M16.24 7.76a6 6 0 0 1 0 8.49m-8.48-.01a6 6 0 0 1 0-8.49m11.31-2.82a10 10 0 0 1 0 14.14m-14.14 0a10 10 0 0 1 0-14.14"/>
                </svg>
              </div>
              <div *ngFor="let topic of topics" 
                   class="p-4 border-b border-gray-800 hover:bg-gray-900 cursor-pointer flex justify-between items-center group">
              <div>
                <h4 class="text-white font-bold group-hover:text-[#39ff14] transition-colors">{{ topic.title }}</h4>
                <p class="text-xs text-gray-500 mt-1">Operator: {{ topic.author }}</p>
              </div>
              <div class="text-right">
                <span class="block text-[#39ff14] font-bold text-sm">{{ topic.replies }} Replies</span>
                <span class="text-xs text-gray-600">{{ topic.active }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="space-y-6">
          <div class="border border-[#39ff14] p-6 bg-black text-center neon-border">
            <svg class="mx-auto text-[#39ff14] mb-4" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
              <circle cx="9" cy="7" r="4"/>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
              <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
            </svg>
            <h3 class="text-white font-bold text-xl mb-2">Join the Ranks</h3>
            <p class="text-gray-400 text-sm mb-4">Connect with 15,000+ users. Share plugins, configs, and hardware setups.</p>
            <button class="w-full bg-[#39ff14] text-black font-bold py-3 uppercase hover:bg-white transition-colors">
              Enlist Now
            </button>
          </div>
          
          <div class="border border-gray-800 p-6 bg-black">
            <h3 class="text-white font-bold mb-2 flex items-center gap-2">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="2" y="2" width="20" height="8" rx="2" ry="2"/>
                <rect x="2" y="14" width="20" height="8" rx="2" ry="2"/>
                <line x1="6" y1="6" x2="6.01" y2="6"/>
                <line x1="6" y1="18" x2="6.01" y2="18"/>
              </svg>
              Status
            </h3>
            <div class="space-y-2 text-sm">
              <div class="flex justify-between">
                <span class="text-gray-400">Mainnet</span>
                <span class="text-[#39ff14]">ONLINE</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-400">Plugin Repo</span>
                <span class="text-[#39ff14]">ONLINE</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-400">Forum</span>
                <span class="text-[#39ff14]">ONLINE</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      </div>
    </div>
  `
})
export class CommunityComponent {
  topics: ForumTopic[] = [
    { 
      title: 'Custom Dashboard Configs', 
      author: 'RangerOne', 
      replies: 42, 
      active: '2m ago' 
    },
    { 
      title: '[Plugin] Local LLM Integration Guide', 
      author: 'NeuralKnight', 
      replies: 156, 
      active: '1h ago' 
    },
    { 
      title: 'Troubleshooting: Z-Wave Mesh', 
      author: 'CommsOfficer', 
      replies: 8, 
      active: '3h ago' 
    },
    { 
      title: 'Show your battle stations', 
      author: 'EchoBase', 
      replies: 890, 
      active: '5m ago' 
    }
  ];
}
