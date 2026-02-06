import { Component, OnInit, OnDestroy, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-system-log',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="w-full h-48 md:h-full md:w-64 bg-black border-r border-[#39ff14] font-mono text-xs overflow-hidden flex flex-col neon-border md:border-r md:border-t-0 md:border-b-0 border-b">
      <div class="flex items-center space-x-2 p-4 pb-2 border-b border-[#39ff14]">
        <svg class="text-[#39ff14] animate-pulse" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
        </svg>
        <span class="text-[#39ff14] font-bold">LIVE SECURITY LOG</span>
      </div>
      <div #logContainer class="flex-1 overflow-y-auto space-y-1 text-green-500 opacity-80 p-4">
        <div *ngFor="let log of logs">{{ log }}</div>
      </div>
      <div class="border-t border-gray-800 p-4 space-y-2">
        <div class="flex justify-between text-gray-600 text-[10px]">
          <span>UPTIME</span>
          <span class="text-[#39ff14]">{{ uptime }}</span>
        </div>
        <div class="flex justify-between text-gray-600 text-[10px]">
          <span>EVENTS</span>
          <span class="text-[#39ff14]">{{ eventCount }}</span>
        </div>
        <div class="flex justify-between text-gray-600 text-[10px]">
          <span>THREATS</span>
          <span class="text-red-500">0</span>
        </div>
      </div>
    </div>
  `
})
export class SystemLogComponent implements OnInit, OnDestroy, AfterViewChecked {
  @ViewChild('logContainer') private logContainer!: ElementRef;
  logs: string[] = [
    '[SYSTEM] Core initialized...',
    '[SECURE] Local environment confirmed.',
    '[NETWORK] Port 8000 active.'
  ];
  
  private interval: any;
  private shouldScroll = false;
  uptime: string = '00:00:00';
  eventCount: number = 0;
  private startTime: number = Date.now();

  ngOnInit() {
    this.interval = setInterval(() => {
      this.addLog();
      this.updateStats();
    }, 1500);
  }

  ngOnDestroy() {
    if (this.interval) {
      clearInterval(this.interval);
    }
  }

  ngAfterViewChecked() {
    if (this.shouldScroll) {
      this.scrollToBottom();
      this.shouldScroll = false;
    }
  }

  private addLog() {
    const actions = ['SCANNING', 'ENCRYPTING', 'MONITORING', 'ANALYZING', 'LOCKED'];
    const targets = ['Traffic', 'Packet 404', 'Backdoor', 'Neural Net', 'Smart Fridge', 'Camera Feed 04'];
    const action = actions[Math.floor(Math.random() * actions.length)];
    const target = targets[Math.floor(Math.random() * targets.length)];
    const time = new Date().toLocaleTimeString('en-US', { hour12: false });
    
    this.logs.push(`[${time}] ${action} :: ${target}`);
    if (this.logs.length > 15) {
      this.logs.shift();
    }
    this.eventCount++;
    this.shouldScroll = true;
  }

  private updateStats() {
    const elapsed = Date.now() - this.startTime;
    const hours = Math.floor(elapsed / 3600000);
    const minutes = Math.floor((elapsed % 3600000) / 60000);
    const seconds = Math.floor((elapsed % 60000) / 1000);
    this.uptime = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  }

  private scrollToBottom() {
    try {
      this.logContainer.nativeElement.scrollTop = this.logContainer.nativeElement.scrollHeight;
    } catch(err) { }
  }
}
