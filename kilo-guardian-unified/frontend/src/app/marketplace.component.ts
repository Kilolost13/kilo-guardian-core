import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

interface MarketplaceItem {
  name: string;
  price: string;
  type: string;
  desc: string;
}

@Component({
  selector: 'app-marketplace',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="h-full w-full p-4 md:p-6 lg:p-8 grid-bg overflow-y-auto">
      <div class="max-w-7xl mx-auto w-full">
        <div class="flex justify-between items-end border-b border-[#39ff14] pb-4 mb-8">
          <div>
            <h2 class="text-3xl md:text-4xl font-header text-white">Supply Depot</h2>
            <p class="text-[#39ff14] text-xs md:text-sm tracking-widest">AUTHORIZED HARDWARE & SOFTWARE</p>
          </div>
          <div class="text-right hidden md:block">
            <p class="text-xs text-gray-500">SECURE CONNECTION ESTABLISHED</p>
            <p class="text-xs text-gray-500">ID: KILO-ACTUAL</p>
          </div>
        </div>
        
        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 md:gap-6">
        <div *ngFor="let item of items" 
             class="border border-gray-800 bg-[#0a0a0a] p-4 flex flex-col justify-between hover:neon-border transition-all">
          <div>
            <div class="flex justify-between mb-2">
              <span class="text-xs bg-gray-900 text-gray-400 px-2 py-1">{{ item.type }}</span>
              <span *ngIf="item.price === '$0.00'" 
                    class="text-xs bg-[#39ff14] text-black px-2 py-1 font-bold">FREE</span>
            </div>
            <h3 class="text-lg font-bold text-white font-header">{{ item.name }}</h3>
            <p class="text-gray-400 text-sm mt-2 mb-4">{{ item.desc }}</p>
          </div>
          <div class="flex justify-between items-center mt-4 border-t border-gray-800 pt-4">
            <span class="text-xl font-bold text-[#39ff14]">{{ item.price }}</span>
            <button class="bg-gray-800 hover:bg-[#39ff14] hover:text-black text-white px-4 py-2 text-sm uppercase font-bold transition-colors">
              Requisition
            </button>
          </div>
        </div>
      </div>
    </div>
  `
})
export class MarketplaceComponent {
  items: MarketplaceItem[] = [
    { 
      name: 'Bastion Core (Pi 5 Kit)', 
      price: '$129.99', 
      type: 'UNIT', 
      desc: 'The brain. Raspberry Pi 5, Custom Case, Pre-flashed SD.' 
    },
    { 
      name: 'Sentinel Cam Mk.II', 
      price: '$89.99', 
      type: 'VISION', 
      desc: 'PoE, Night Vision, On-device person detection integration.' 
    },
    { 
      name: 'Gigabit PoE+ Switch', 
      price: '$149.99', 
      type: 'NET', 
      desc: 'Ruggedized 8-port switch. 120W budget. VLAN ready.' 
    },
    { 
      name: 'Sensor Array Pack', 
      price: '$45.00', 
      type: 'SENSE', 
      desc: '5x Door/Window sensors (Zigbee). Long range.' 
    },
    { 
      name: 'Plugin: Adv. Crypto', 
      price: '$0.00', 
      type: 'SOFT', 
      desc: 'Real-time market tracking and wallet alerts.' 
    },
    { 
      name: 'Plugin: Threat Radar', 
      price: '$0.00', 
      type: 'SOFT', 
      desc: 'Network intrusion detection system visualizer.' 
    }
  ];
}
