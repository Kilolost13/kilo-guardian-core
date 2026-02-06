import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

interface Feature {
  icon: string;
  title: string;
  desc: string;
}

@Component({
  selector: 'app-features',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="h-full w-full p-4 md:p-6 lg:p-8 grid-bg overflow-y-auto">
      <div class="max-w-7xl mx-auto w-full">
        <h2 class="text-3xl md:text-4xl font-header text-white mb-6 md:mb-8 border-b border-[#39ff14] pb-4 inline-block">
          Tactical Capabilities
        </h2>
        
        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 md:gap-6">
          <div *ngFor="let feature of features" 
               class="bg-black border border-gray-800 p-5 md:p-6 hover:border-[#39ff14] transition-all group relative overflow-hidden">
            <div class="absolute top-0 right-0 p-2 opacity-20 group-hover:opacity-100 transition-opacity">
              <div [innerHTML]="feature.icon" class="text-[#39ff14] w-10 h-10 md:w-12 md:h-12"></div>
            </div>
            
            <h3 class="text-lg md:text-xl font-bold text-white mb-2 font-header group-hover:text-[#39ff14]">
              {{ feature.title }}
            </h3>
            
            <p class="text-gray-400 text-sm leading-relaxed">{{ feature.desc }}</p>
            
            <div class="mt-4 w-full h-1 bg-gray-900 overflow-hidden">
              <div class="h-full bg-[#39ff14] w-0 group-hover:w-full transition-all duration-700"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `
})
export class FeaturesComponent {
  features: Feature[] = [
    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>',
      title: 'Daily Intel Briefings',
      desc: 'Morning, Evening, and Quick updates generated locally. Integrates News, Weather, and Calendar.'
    },
    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="5" y="11" width="14" height="10" rx="2"/><circle cx="12" cy="16" r="1"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>',
      title: 'Perimeter Security',
      desc: 'Monitors door sensors and cameras. Alerts you if a door is open >15 mins. Logs anomaly motion events.'
    },
    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
      title: 'Task Operations',
      desc: 'Intelligent task matching via Email parsing. \'Bill due\' emails become Monday tasks automatically.'
    },
    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>',
      title: '100% Local Data',
      desc: 'No cloud surveillance. Your data stays on your hardware. You own the keys.'
    },
    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="4" width="6" height="7"/><rect x="4" y="15" width="6" height="5"/><rect x="14" y="4" width="6" height="5"/><rect x="14" y="13" width="6" height="7"/></svg>',
      title: 'Plugin Architecture',
      desc: 'Modular Python-based plugin system. Extend capabilities via the community marketplace.'
    },
    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>',
      title: 'Pattern Recognition',
      desc: 'Learns your routines over time to optimize schedule suggestions and health tracking.'
    }
  ];
}
