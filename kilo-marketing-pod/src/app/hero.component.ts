import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Output } from '@angular/core';
import { ChatComponent } from './chat.component';

@Component({
  selector: 'app-hero',
  standalone: true,
  imports: [CommonModule, ChatComponent],
  template: `
    <div class="h-full w-full p-4 md:p-8 lg:p-12 flex flex-col relative overflow-y-auto grid-bg">
      <div class="max-w-6xl mx-auto w-full z-10 py-8">
        <div class="flex items-center space-x-4 mb-4">
          <div class="h-1 w-16 md:w-24 bg-[#39ff14]"></div>
          <span class="text-[#39ff14] tracking-[0.3em] uppercase text-xs md:text-sm">System Version 2.0</span>
        </div>

        <!-- Chat UI -->
        <div class="mt-8">
          <app-chat></app-chat>
        </div>
        
        <h1 class="text-4xl md:text-6xl lg:text-8xl font-header font-black text-white mb-6 uppercase leading-none">
          Kilo's <span class="neon-text">Bastion</span>
        </h1>
        
        <p class="text-base md:text-xl lg:text-2xl text-gray-400 mb-6 max-w-3xl leading-relaxed border-l-4 border-[#39ff14] pl-4 md:pl-6">
          Your digital fortress. Local-first AI that tracks your life, secures your network, and briefs you like a commander. No cloud. No leaks.
        </p>
        
        <p class="text-sm md:text-base text-gray-500 mb-8 max-w-3xl leading-relaxed pl-4 md:pl-6">
          The AI doesn't live in the cloud—it lives in your appliance. On your network. Under your control. 
          Kilo's Bastion watches your cameras, reads your emails, tracks your calendar, and gives you the briefing you need, when you need it.
        </p>
        
        <div class="flex flex-col sm:flex-row gap-4 md:gap-6 mb-12">
          <button (click)="onNavigate('install')" 
                  class="bg-[#39ff14] text-black px-8 md:px-12 py-4 md:py-5 font-bold text-lg md:text-xl uppercase tracking-wider hover:bg-white transition-colors flex items-center justify-center gap-3 clip-path-button">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            Initialize System
          </button>
          
          <button (click)="onNavigate('marketplace')" 
                  class="border-2 border-[#39ff14] text-[#39ff14] px-8 md:px-12 py-4 md:py-5 font-bold text-lg md:text-xl uppercase tracking-wider hover:bg-[#39ff14] hover:text-black transition-colors flex items-center justify-center gap-3">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <circle cx="12" cy="12" r="3"/>
              <line x1="12" y1="1" x2="12" y2="3"/>
              <line x1="12" y1="21" x2="12" y2="23"/>
              <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
              <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
              <line x1="1" y1="12" x2="3" y2="12"/>
              <line x1="21" y1="12" x2="23" y2="12"/>
              <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
              <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
            </svg>
            Upgrade Hardware
          </button>
        </div>
        
        <!-- Core Features Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-8">
          <div class="border border-gray-800 bg-black/50 p-6 hover:border-[#39ff14] transition-colors">
            <div class="text-[#39ff14] mb-3 text-2xl">🎥</div>
            <h3 class="text-white font-bold mb-2 uppercase text-sm tracking-wider">Live Surveillance</h3>
            <p class="text-gray-500 text-xs leading-relaxed">Real-time camera feeds with motion detection and facial recognition</p>
          </div>
          
          <div class="border border-gray-800 bg-black/50 p-6 hover:border-[#39ff14] transition-colors">
            <div class="text-[#39ff14] mb-3 text-2xl">📧</div>
            <h3 class="text-white font-bold mb-2 uppercase text-sm tracking-wider">Email Intelligence</h3>
            <p class="text-gray-500 text-xs leading-relaxed">AI-powered inbox summaries and priority alerts</p>
          </div>
          
          <div class="border border-gray-800 bg-black/50 p-6 hover:border-[#39ff14] transition-colors">
            <div class="text-[#39ff14] mb-3 text-2xl">📅</div>
            <h3 class="text-white font-bold mb-2 uppercase text-sm tracking-wider">Calendar Sync</h3>
            <p class="text-gray-500 text-xs leading-relaxed">Never miss a meeting with smart scheduling integration</p>
          </div>
          
          <div class="border border-gray-800 bg-black/50 p-6 hover:border-[#39ff14] transition-colors">
            <div class="text-[#39ff14] mb-3 text-2xl">🔒</div>
            <h3 class="text-white font-bold mb-2 uppercase text-sm tracking-wider">Network Defense</h3>
            <p class="text-gray-500 text-xs leading-relaxed">Intrusion detection and automated threat response</p>
          </div>
          
          <div class="border border-gray-800 bg-black/50 p-6 hover:border-[#39ff14] transition-colors">
            <div class="text-[#39ff14] mb-3 text-2xl">💰</div>
            <h3 class="text-white font-bold mb-2 uppercase text-sm tracking-wider">Finance Tracking</h3>
            <p class="text-gray-500 text-xs leading-relaxed">Automated expense tracking and budget monitoring</p>
          </div>
          
          <div class="border border-gray-800 bg-black/50 p-6 hover:border-[#39ff14] transition-colors">
            <div class="text-[#39ff14] mb-3 text-2xl">🧠</div>
            <h3 class="text-white font-bold mb-2 uppercase text-sm tracking-wider">Daily Briefings</h3>
            <p class="text-gray-500 text-xs leading-relaxed">Morning summaries with weather, news, and priorities</p>
          </div>
        </div>
      </div>
      
      <!-- Decorative background element -->
      <div class="absolute right-0 top-1/2 transform -translate-y-1/2 opacity-10 pointer-events-none hidden lg:block">
        <svg width="600" height="600" viewBox="0 0 24 24" fill="none" stroke="#39ff14" stroke-width="0.5">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
        </svg>
      </div>
    </div>
  `
})
export class HeroComponent {
  @Output() navigate = new EventEmitter<string>();

  onNavigate(view: string) {
    this.navigate.emit(view);
  }
}
