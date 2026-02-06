import { Component, OnInit } from '@angular/core';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { Title } from '@angular/platform-browser';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-status-bar',
  standalone: true,
  imports: [CommonModule, HttpClientModule],
  template: `
    <div class="status-bar">
      <div class="brand">KILO_OS [GUARDIAN]</div>
      
      <div class="status-indicator" [ngClass]="getStatusClass()">
        <span class="light-icon">●</span>
        <span>SYSTEM {{ systemStatus }}</span>
        <span class="details">[{{ statusMessage }}]</span>
      </div>
    </div>
  `
})
export class StatusBarComponent implements OnInit {
  systemStatus: string = 'GREEN';
  statusMessage: string = 'Initializing...';

  constructor(private http: HttpClient, private titleService: Title) {}

  ngOnInit() {
    // Poll system health every 5 seconds
    setInterval(() => this.checkHealth(), 5000);
    this.checkHealth();
  }

  checkHealth() {
    this.http.get<any>('http://localhost:8001/api/system/health').subscribe(data => {
      this.systemStatus = data.status;
      this.statusMessage = data.message;
      this.updateBrowserTab(data.status);
    });
  }

  getStatusClass() {
    if (this.systemStatus === 'RED') return 'glow-red';
    if (this.systemStatus === 'YELLOW') return 'glow-yellow';
    return 'glow-green';
  }

  // UPDATES THE BROWSER TAB TITLE
  updateBrowserTab(status: string) {
    if (status === 'RED') this.titleService.setTitle('🔴 CRITICAL - KILO');
    else if (status === 'YELLOW') this.titleService.setTitle('🟡 WARNING - KILO');
    else this.titleService.setTitle('🟢 Kilo Operational');
  }
}
