import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-nav-sidebar',
  standalone: true,
  imports: [CommonModule],
  template: `
    <nav class="w-full md:w-24 bg-black border-r border-[#39ff14] flex md:flex-col justify-center items-center p-2 z-20 neon-border">
      <div class="hidden md:block absolute top-4">
        <svg class="text-[#39ff14]" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
        </svg>
      </div>
      
      <div class="flex md:flex-col gap-4">
        <button (click)="navigate('home')" 
                [class]="getButtonClass('home')" 
                title="Home">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="7" height="7"/>
            <rect x="14" y="3" width="7" height="7"/>
            <rect x="14" y="14" width="7" height="7"/>
            <rect x="3" y="14" width="7" height="7"/>
          </svg>
        </button>
        
        <button (click)="navigate('features')" 
                [class]="getButtonClass('features')" 
                title="Features">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="4" y="4" width="6" height="7"/>
            <rect x="4" y="15" width="6" height="5"/>
            <rect x="14" y="4" width="6" height="5"/>
            <rect x="14" y="13" width="6" height="7"/>
          </svg>
        </button>
        
        <button (click)="navigate('marketplace')" 
                [class]="getButtonClass('marketplace')" 
                title="Marketplace">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="9" cy="21" r="1"/>
            <circle cx="20" cy="21" r="1"/>
            <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/>
          </svg>
        </button>
        
        <button (click)="navigate('community')" 
                [class]="getButtonClass('community')" 
                title="Community">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
            <circle cx="9" cy="7" r="4"/>
            <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
            <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
          </svg>
        </button>
        
        <button (click)="navigate('vpn')" 
                [class]="getButtonClass('vpn')" 
                title="VPN">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="2" y="7" width="20" height="14" rx="2" ry="2"/>
            <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>
          </svg>
        </button>
      </div>
      
      <div class="hidden md:block absolute bottom-4 text-xs text-[#39ff14] font-bold -rotate-90 whitespace-nowrap">
        V 2.0.1
      </div>
    </nav>
  `,
  styles: [`
    button {
      @apply p-3 rounded transition-colors;
    }
    .active {
      @apply bg-[#39ff14] text-black;
    }
    .inactive {
      @apply text-gray-500 hover:text-[#39ff14];
    }
  `]
})
export class NavSidebarComponent {
  @Input() currentView: string = 'home';
  @Output() viewChange = new EventEmitter<string>();

  navigate(view: string) {
    this.viewChange.emit(view);
  }

  getButtonClass(view: string): string {
    return view === this.currentView ? 'active' : 'inactive';
  }
}
